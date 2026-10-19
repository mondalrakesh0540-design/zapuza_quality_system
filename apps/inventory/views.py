from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from apps.accounts.models import UserRole
from apps.accounts.permissions import role_required
from apps.audit_trail.models import AuditLog
from .models import (
    IntakeStatus,
    LabStatus,
    MaterialGrade,
    MaterialLabTest,
    QuantityUnit,
    RawMaterialIntake,
    SNCRDisposition,
    SNCRReasonCategory,
    SupplierNCR,
)


@login_required
def intake_list(request):
    status_filter = request.GET.get('status')
    lab_filter = request.GET.get('lab_status')
    grade_filter = request.GET.get('grade')
    search_query = request.GET.get('q', '').strip()

    lots = RawMaterialIntake.objects.select_related('material_grade', 'received_by').all()

    if status_filter:
        lots = lots.filter(status=status_filter)
    if lab_filter:
        lots = lots.filter(lab_status=lab_filter)
    if grade_filter:
        lots = lots.filter(material_grade_id=grade_filter)
    if search_query:
        lots = lots.filter(
            models.Q(lot_number__icontains=search_query) |
            models.Q(heat_number__icontains=search_query) |
            models.Q(supplier_name__icontains=search_query) |
            models.Q(purchase_order_no__icontains=search_query)
        )

    # Enrich each lot with live clearance status
    enriched_lots = []
    for lot in lots:
        can_issue, issue_reason = lot.can_issue_to_production()
        enriched_lots.append({
            'lot': lot,
            'can_issue': can_issue,
            'issue_reason': issue_reason,
        })

    grades = MaterialGrade.objects.filter(is_active=True)

    return render(request, 'inventory/intake_list.html', {
        'lots': enriched_lots,
        'grades': grades,
        'selected_status': status_filter,
        'selected_lab': lab_filter,
        'selected_grade': grade_filter,
        'search_query': search_query,
        'intake_statuses': IntakeStatus.choices,
        'lab_statuses': LabStatus.choices,
    })


@login_required
def intake_detail(request, pk):
    lot = get_object_or_404(
        RawMaterialIntake.objects.select_related('material_grade', 'received_by', 'mtc_verified_by'),
        pk=pk
    )
    can_issue, issue_reason = lot.can_issue_to_production()
    lab_tests = lot.lab_tests.select_related('tested_by').order_by('-created_at')
    ncrs = lot.ncrs.select_related('logged_by').order_by('-created_at')

    return render(request, 'inventory/intake_detail.html', {
        'lot': lot,
        'can_issue': can_issue,
        'issue_reason': issue_reason,
        'lab_tests': lab_tests,
        'ncrs': ncrs,
    })


@login_required
@role_required(UserRole.SHIFT_SUPERVISOR, UserRole.QA_FLOOR_INSPECTOR, UserRole.PLANT_MANAGER)
def intake_create(request):
    """
    Dock Intake Entry form.
    Mandates MTC document upload and heat number logging.
    """
    if request.method == 'POST':
        lot_number = request.POST.get('lot_number', '').strip()
        heat_number = request.POST.get('heat_number', '').strip().upper()
        supplier_name = request.POST.get('supplier_name', '').strip()
        purchase_order_no = request.POST.get('purchase_order_no', '').strip().upper()
        material_grade_id = request.POST.get('material_grade')
        quantity_str = request.POST.get('quantity_received', '').strip()
        unit = request.POST.get('unit', QuantityUnit.KG)
        notes = request.POST.get('notes', '').strip()
        mtc_file = request.FILES.get('mtc_file')

        # Mandatory MTC Verification check (Section 3.2: Intake cannot be saved without MTC file)
        if not mtc_file:
            messages.error(request, "Mandatory MTC Requirement: Intake cannot be saved without an attached Mill Test Certificate (MTC) file.")
            return render(request, 'inventory/intake_form.html', {
                'grades': MaterialGrade.objects.filter(is_active=True),
                'units': QuantityUnit.choices,
            })

        if not heat_number:
            messages.error(request, "Mandatory Heat Number: A valid mill heat number must be recorded for traceability.")
            return render(request, 'inventory/intake_form.html', {
                'grades': MaterialGrade.objects.filter(is_active=True),
                'units': QuantityUnit.choices,
            })

        # Auto-generate lot number if left blank
        if not lot_number:
            count = RawMaterialIntake.objects.count() + 1
            lot_number = f"LOT-{timezone.now().year}-{count:03d}"

        try:
            grade = get_object_or_404(MaterialGrade, pk=material_grade_id)
            quantity = Decimal(quantity_str)

            # Determine initial lab status
            lab_status = LabStatus.IN_LAB_TESTING if grade.requires_lab_testing else LabStatus.NOT_REQUIRED

            barcode = f"RAW-{lot_number}-{heat_number}"

            intake = RawMaterialIntake.objects.create(
                lot_number=lot_number,
                heat_number=heat_number,
                supplier_name=supplier_name,
                purchase_order_no=purchase_order_no,
                material_grade=grade,
                quantity_received=quantity,
                unit=unit,
                mtc_file=mtc_file,
                mtc_verified=False,
                lab_status=lab_status,
                status=IntakeStatus.IN_STORE,
                barcode_identifier=barcode,
                received_by=request.user,
                notes=notes,
            )

            AuditLog.log(
                action=AuditLog.ActionType.RAW_INTAKE,
                user=request.user,
                request=request,
                model_name='RawMaterialIntake',
                object_id=str(intake.id),
                object_repr=intake.lot_number,
                new_value={
                    'lot': intake.lot_number,
                    'heat': intake.heat_number,
                    'grade': grade.code,
                    'qty': str(quantity),
                    'lab_status': lab_status
                },
                details=f"Raw material lot {intake.lot_number} received at dock with Heat #{heat_number}. MTC attached. Initial lab status: {lab_status}."
            )

            messages.success(request, f"Raw material intake {intake.lot_number} (Heat #{heat_number}) successfully recorded.")
            return redirect('inventory:intake_detail', pk=intake.pk)

        except Exception as e:
            messages.error(request, f"Error saving dock intake: {str(e)}")

    return render(request, 'inventory/intake_form.html', {
        'grades': MaterialGrade.objects.filter(is_active=True),
        'units': QuantityUnit.choices,
    })


@login_required
@role_required(UserRole.QUALITY_ENGINEER, UserRole.QUALITY_MANAGER, UserRole.PLANT_MANAGER)
def mtc_verify(request, pk):
    """
    Quality Engineer / Quality Manager MTC Verification workflow.
    """
    lot = get_object_or_404(RawMaterialIntake, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'verify':
            lot.mtc_verified = True
            lot.mtc_verified_by = request.user
            lot.mtc_verified_at = timezone.now()
            lot.save(update_fields=['mtc_verified', 'mtc_verified_by', 'mtc_verified_at'])

            AuditLog.log(
                action=AuditLog.ActionType.MTC_VERIFIED,
                user=request.user,
                request=request,
                model_name='RawMaterialIntake',
                object_id=str(lot.id),
                object_repr=lot.lot_number,
                details=f"Mill Test Certificate for Lot {lot.lot_number} verified and approved by {request.user.employee_id}."
            )
            messages.success(request, f"MTC for Lot {lot.lot_number} (Heat #{lot.heat_number}) verified and approved.")
        elif action == 'reject':
            return redirect('inventory:sncr_create', pk=lot.pk)

        return redirect('inventory:intake_detail', pk=lot.pk)

    return render(request, 'inventory/mtc_verify.html', {
        'lot': lot,
    })


@login_required
@role_required(UserRole.QUALITY_ENGINEER, UserRole.QUALITY_MANAGER, UserRole.PLANT_MANAGER)
def lab_test_create(request, pk):
    """
    Record internal spectro-chemical analysis and mechanical testing results.
    Automates tolerance comparison against MaterialGrade.
    """
    lot = get_object_or_404(RawMaterialIntake.objects.select_related('material_grade'), pk=pk)
    grade = lot.material_grade

    if request.method == 'POST':
        try:
            c = request.POST.get('carbon_actual') or None
            mn = request.POST.get('manganese_actual') or None
            si = request.POST.get('silicon_actual') or None
            p = request.POST.get('phosphorus_actual') or None
            s = request.POST.get('sulfur_actual') or None

            yield_val = request.POST.get('yield_strength_actual') or None
            tensile_val = request.POST.get('tensile_strength_actual') or None
            hardness_val = request.POST.get('hardness_actual') or None

            lab_report = request.FILES.get('lab_report_file')

            test = MaterialLabTest(
                intake=lot,
                tested_by=request.user,
                carbon_actual=Decimal(c) if c else None,
                manganese_actual=Decimal(mn) if mn else None,
                silicon_actual=Decimal(si) if si else None,
                phosphorus_actual=Decimal(p) if p else None,
                sulfur_actual=Decimal(s) if s else None,
                yield_strength_actual=Decimal(yield_val) if yield_val else None,
                tensile_strength_actual=Decimal(tensile_val) if tensile_val else None,
                hardness_actual=Decimal(hardness_val) if hardness_val else None,
                lab_report_file=lab_report,
            )
            test.save()

            AuditLog.log(
                action=AuditLog.ActionType.LAB_TEST,
                user=request.user,
                request=request,
                model_name='MaterialLabTest',
                object_id=str(test.id),
                object_repr=f"{lot.lot_number} Lab Test",
                new_value={'is_passed': test.is_passed, 'summary': test.evaluation_summary},
                details=f"Material lab analysis recorded for Lot {lot.lot_number}. Result: {'PASSED' if test.is_passed else 'FAILED'}."
            )

            if test.is_passed:
                messages.success(request, f"Lab analysis PASSED for Lot {lot.lot_number}. Grade specifications conform.")
            else:
                messages.warning(
                    request,
                    f"Lab analysis FAILED for Lot {lot.lot_number}: {test.evaluation_summary}. "
                    "Lot has been marked as Lab Rejected. You may now generate a Supplier Non-Conformance Report (SNCR)."
                )

            return redirect('inventory:intake_detail', pk=lot.pk)

        except Exception as e:
            messages.error(request, f"Error saving laboratory test: {str(e)}")

    return render(request, 'inventory/lab_test_form.html', {
        'lot': lot,
        'grade': grade,
    })


@login_required
@role_required(UserRole.SHIFT_SUPERVISOR, UserRole.QUALITY_ENGINEER, UserRole.QUALITY_MANAGER, UserRole.PLANT_MANAGER)
def sncr_create(request, pk):
    """
    Log a Supplier Non-Conformance Report and place lot in Supplier Quarantine.
    """
    lot = get_object_or_404(RawMaterialIntake, pk=pk)

    if request.method == 'POST':
        reason_category = request.POST.get('reason_category', SNCRReasonCategory.CHEMICAL_OUT_OF_SPEC)
        disposition = request.POST.get('disposition', SNCRDisposition.SUPPLIER_QUARANTINE_HOLD)
        defect_description = request.POST.get('defect_description', '').strip()
        corrective_action = request.POST.get('corrective_action_requested', '').strip()

        # Generate unique SNCR number
        count = SupplierNCR.objects.count() + 1
        sncr_number = f"SNCR-{timezone.now().year}-{count:03d}"

        sncr = SupplierNCR.objects.create(
            sncr_number=sncr_number,
            intake=lot,
            logged_by=request.user,
            reason_category=reason_category,
            disposition=disposition,
            defect_description=defect_description,
            corrective_action_requested=corrective_action,
        )

        AuditLog.log(
            action=AuditLog.ActionType.SNCR_LOGGED,
            user=request.user,
            request=request,
            model_name='SupplierNCR',
            object_id=str(sncr.id),
            object_repr=sncr.sncr_number,
            new_value={'sncr': sncr.sncr_number, 'lot': lot.lot_number, 'disposition': disposition},
            details=f"SNCR {sncr.sncr_number} logged for Lot {lot.lot_number}. Lot placed in SUPPLIER QUARANTINE."
        )

        AuditLog.log(
            action=AuditLog.ActionType.QUARANTINE_MOVED,
            user=request.user,
            request=request,
            model_name='RawMaterialIntake',
            object_id=str(lot.id),
            object_repr=lot.lot_number,
            details=f"Lot {lot.lot_number} (Heat #{lot.heat_number}) quarantined due to SNCR {sncr.sncr_number}."
        )

        messages.error(
            request,
            f"Supplier Non-Conformance {sncr.sncr_number} recorded. Lot {lot.lot_number} has been tagged as "
            "SUPPLIER QUARANTINE and is strictly locked from production work orders."
        )
        return redirect('inventory:sncr_list')

    return render(request, 'inventory/sncr_form.html', {
        'lot': lot,
        'reasons': SNCRReasonCategory.choices,
        'dispositions': SNCRDisposition.choices,
    })


@login_required
def sncr_list(request):
    """List of all Supplier Non-Conformance Reports and quarantined stock."""
    ncrs = SupplierNCR.objects.select_related('intake', 'logged_by', 'intake__material_grade').all()
    quarantined_lots = RawMaterialIntake.objects.filter(status=IntakeStatus.QUARANTINED)

    return render(request, 'inventory/sncr_list.html', {
        'ncrs': ncrs,
        'quarantined_lots': quarantined_lots,
    })


@login_required
def traceability_query(request):
    """
    BRD Section 7.2 Forward Recall Traceability.
    Allows searching by heat number to reveal complete provenance.
    """
    query = request.GET.get('heat_number', '').strip().upper()
    lots = []
    if query:
        lots = RawMaterialIntake.objects.select_related(
            'material_grade', 'received_by', 'mtc_verified_by'
        ).prefetch_related('lab_tests', 'ncrs').filter(
            models.Q(heat_number__iexact=query) |
            models.Q(lot_number__iexact=query)
        )

    return render(request, 'inventory/traceability.html', {
        'query': query,
        'lots': lots,
    })
