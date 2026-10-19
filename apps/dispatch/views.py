from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from apps.accounts.permissions import role_required
from apps.accounts.models import UserRole
from apps.audit_trail.models import AuditLog
from apps.production.models import JobTraveler, JobTravelerStatus, OperationStatus
from apps.quality.models import CertificateOfConformance, CertificateStatus
from .models import DispatchManifest, DispatchManifestStatus


@login_required
def dispatch_queue_view(request):
    """
    Central Pre-Dispatch Clearance Queue and Shipping Interlock Dashboard.
    Conforms to BRD Section 10.1 & 10.2.
    """
    filter_status = request.GET.get('status', '')
    search_query = request.GET.get('q', '').strip()

    # Query all completed or active travelers
    travelers = JobTraveler.objects.select_related(
        'work_order',
        'work_order__part',
        'work_order__raw_material_lot',
    ).prefetch_related('operations', 'certificates', 'dispatch_manifests').all()

    if search_query:
        travelers = travelers.filter(
            models.Q(traveler_barcode__icontains=search_query) |
            models.Q(work_order__work_order_number__icontains=search_query) |
            models.Q(work_order__part__part_number__icontains=search_query)
        )

    queue_items = []
    ready_count = 0
    cleared_count = 0
    locked_count = 0

    for trv in travelers:
        can_clear, reasons = DispatchManifest.validate_shipping_interlock(trv)
        manifest = trv.dispatch_manifests.order_by('-cleared_at').first()
        active_coc = trv.certificates.filter(status=CertificateStatus.ACTIVE).first()

        if manifest:
            stage = 'dispatched' if manifest.status == DispatchManifestStatus.DISPATCHED else 'cleared'
            cleared_count += 1
        elif can_clear:
            stage = 'ready'
            ready_count += 1
        else:
            stage = 'locked'
            locked_count += 1

        if filter_status and stage != filter_status:
            continue

        queue_items.append({
            'traveler': trv,
            'can_clear': can_clear,
            'lockout_reasons': reasons,
            'manifest': manifest,
            'coc': active_coc,
            'stage': stage,
        })

    return render(request, 'dispatch/dispatch_queue.html', {
        'queue_items': queue_items,
        'ready_count': ready_count,
        'cleared_count': cleared_count,
        'locked_count': locked_count,
        'selected_status': filter_status,
        'search_query': search_query,
    })


@login_required
def dispatch_create_view(request, traveler_id):
    """
    Process Shipping Gate Pass Clearance & Log Dispatch Manifest.
    Strictly blocked if shipping interlock fails or user lacks clearance permission.
    """
    if not request.user.can_clear_shipping:
        AuditLog.log(
            action=AuditLog.ActionType.SECURITY_ALERT,
            user=request.user,
            request=request,
            model_name='DispatchManifest',
            object_id=str(traveler_id),
            object_repr=f"Traveler ID {traveler_id}",
            details=f"User {request.user.employee_id} ({request.user.role}) denied permission to clear shipping dispatch."
        )
        messages.error(request, "Permission Denied: Only Shift Supervisors, Quality Managers, or Plant Managers can issue dispatch clearance.")
        return redirect('dispatch:dispatch_queue')

    traveler = get_object_or_404(
        JobTraveler.objects.select_related(
            'work_order',
            'work_order__part',
            'work_order__raw_material_lot',
        ).prefetch_related('operations', 'certificates'),
        pk=traveler_id
    )

    # Re-validate shipping interlocks on the server
    can_clear, reasons = DispatchManifest.validate_shipping_interlock(traveler)
    if not can_clear:
        lockout_msg = "; ".join(reasons)
        AuditLog.log(
            action=AuditLog.ActionType.SHIPPING_INTERLOCK,
            user=request.user,
            request=request,
            model_name='JobTraveler',
            object_id=str(traveler.id),
            object_repr=traveler.traveler_barcode,
            details=f"Electronic Shipping Interlock enforced for traveler {traveler.traveler_barcode}: {lockout_msg}"
        )
        messages.error(request, f"Electronic Shipping Interlock: Dispatch clearance blocked. Reasons: {lockout_msg}")
        return redirect('dispatch:dispatch_queue')

    active_coc = traveler.certificates.filter(status=CertificateStatus.ACTIVE).first()

    if request.method == 'POST':
        customer_name = request.POST.get('customer_name', '').strip()
        customer_po = request.POST.get('customer_po_number', '').strip()
        destination = request.POST.get('shipping_destination', '').strip()
        vehicle_no = request.POST.get('transport_vehicle_number', '').strip()
        driver_name = request.POST.get('driver_name', '').strip()
        driver_contact = request.POST.get('driver_contact', '').strip()
        driver_license = request.POST.get('driver_license', '').strip()
        seal_no = request.POST.get('container_seal_number', '').strip()
        remarks = request.POST.get('remarks', '').strip()

        try:
            qty = int(request.POST.get('dispatch_quantity', traveler.work_order.completed_quantity))
        except ValueError:
            qty = traveler.work_order.completed_quantity

        if not (customer_name and customer_po and destination and vehicle_no and driver_name):
            messages.error(request, "Missing Required Fields: Customer Name, PO Number, Destination, Vehicle No, and Driver Name are mandatory.")
            return render(request, 'dispatch/manifest_form.html', {
                'traveler': traveler,
                'work_order': traveler.work_order,
                'part': traveler.work_order.part,
                'coc': active_coc,
            })

        with transaction.atomic():
            manifest_number = f"DSP-{traveler.work_order.work_order_number}"
            if DispatchManifest.objects.filter(manifest_number=manifest_number).exists():
                manifest_number = f"DSP-{traveler.work_order.work_order_number}-{int(timezone.now().timestamp())}"

            manifest = DispatchManifest.objects.create(
                manifest_number=manifest_number,
                traveler=traveler,
                work_order=traveler.work_order,
                certificate=active_coc,
                customer_name=customer_name,
                customer_po_number=customer_po,
                shipping_destination=destination,
                dispatch_quantity=qty,
                transport_vehicle_number=vehicle_no,
                driver_name=driver_name,
                driver_contact=driver_contact,
                driver_license=driver_license,
                container_seal_number=seal_no,
                status=DispatchManifestStatus.CLEARED,
                cleared_by=request.user,
                cleared_at=timezone.now(),
                remarks=remarks,
            )

            # Mark traveler as completed and permanently closed on shopfloor per BRD Section 10.2
            traveler.status = JobTravelerStatus.COMPLETED
            traveler.save(update_fields=['status'])

            AuditLog.log(
                action=AuditLog.ActionType.DISPATCH_CLEARED,
                user=request.user,
                request=request,
                model_name='DispatchManifest',
                object_id=str(manifest.id),
                object_repr=manifest.manifest_number,
                details=f"Dispatch Gate Pass {manifest.manifest_number} cleared for Traveler {traveler.traveler_barcode} to customer {customer_name}. Vehicle: {vehicle_no}."
            )

            messages.success(request, f"Dispatch Gate Pass {manifest.manifest_number} successfully cleared! Packing slip and shipping QR labels are unlocked.")
            return redirect('dispatch:dispatch_gate_pass', manifest_id=manifest.id)

    return render(request, 'dispatch/manifest_form.html', {
        'traveler': traveler,
        'work_order': traveler.work_order,
        'part': traveler.work_order.part,
        'coc': active_coc,
    })


@login_required
def dispatch_gate_pass_view(request, manifest_id):
    """
    Print-ready Security Gate Pass & Commercial Packing Slip.
    Conforms to BRD Section 10.2 & 11.1.
    """
    manifest = get_object_or_404(
        DispatchManifest.objects.select_related(
            'traveler',
            'work_order',
            'work_order__part',
            'work_order__part__material_grade',
            'work_order__raw_material_lot',
            'certificate',
            'cleared_by',
        ),
        pk=manifest_id
    )

    domain = request.get_host()
    verify_url = f"{request.scheme}://{domain}/dispatch/verify/{manifest.qr_verification_token}/"

    return render(request, 'dispatch/gate_pass.html', {
        'manifest': manifest,
        'traveler': manifest.traveler,
        'work_order': manifest.work_order,
        'part': manifest.work_order.part,
        'lot': manifest.work_order.raw_material_lot,
        'coc': manifest.certificate,
        'verify_url': verify_url,
    })


@login_required
def dispatch_crate_label_view(request, manifest_id):
    """
    Printable Exterior Shipping Crate QR Label.
    Conforms to BRD Section 11.2 (Customer Verification Labels for crate exteriors).
    """
    manifest = get_object_or_404(
        DispatchManifest.objects.select_related(
            'traveler',
            'work_order',
            'work_order__part',
            'work_order__raw_material_lot',
            'certificate',
            'cleared_by',
        ),
        pk=manifest_id
    )

    domain = request.get_host()
    verify_url = f"{request.scheme}://{domain}/dispatch/verify/{manifest.qr_verification_token}/"

    return render(request, 'dispatch/crate_label.html', {
        'manifest': manifest,
        'traveler': manifest.traveler,
        'work_order': manifest.work_order,
        'part': manifest.work_order.part,
        'lot': manifest.work_order.raw_material_lot,
        'coc': manifest.certificate,
        'verify_url': verify_url,
    })


def customer_shipping_verify_view(request, token):
    """
    Public Customer Shipping & Inspection Verification Endpoint.
    Conforms to BRD Section 11.3:
    Scanning crate QR code opens a secure web document displaying the complete certified quality report
    (nominal specs, actual measured values, lab heat certs, supplier MTCs, and authorized Quality signatures).
    """
    manifest = DispatchManifest.objects.select_related(
        'traveler',
        'work_order',
        'work_order__part',
        'work_order__part__material_grade',
        'work_order__raw_material_lot',
        'work_order__raw_material_lot__material_grade',
        'certificate',
        'cleared_by',
    ).filter(qr_verification_token=token).first()

    if not manifest:
        return render(request, 'dispatch/customer_verify.html', {
            'is_valid': False,
            'token': token,
        })

    pdi_insp = manifest.traveler.get_pdi_inspection()
    measurements = pdi_insp.measurements.select_related('parameter', 'measuring_tool').all() if pdi_insp else []

    return render(request, 'dispatch/customer_verify.html', {
        'is_valid': True,
        'manifest': manifest,
        'traveler': manifest.traveler,
        'work_order': manifest.work_order,
        'part': manifest.work_order.part,
        'lot': manifest.work_order.raw_material_lot,
        'coc': manifest.certificate,
        'pdi_insp': pdi_insp,
        'measurements': measurements,
    })
