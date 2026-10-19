import hashlib
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models, transaction
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from apps.accounts.models import UserRole
from apps.accounts.permissions import role_required
from apps.audit_trail.models import AuditLog
from apps.inventory.models import RawMaterialIntake, IntakeStatus
from apps.master_data.models import InspectionTool, ToolStatus, Workstation
from apps.production.models import JobTraveler, JobTravelerStatus, OperationStatus, TravelerOperation, WorkOrder, WorkOrderStatus
from .models import (
    Blueprint,
    BlueprintPin,
    CertificateOfConformance,
    CertificateStatus,
    ConcessionReason,
    ConcessionRecord,
    FloorInspection,
    FloorInspectionStatus,
    InspectionDefectPhoto,
    InspectionMeasurement,
    InspectionParameter,
    InspectionTemplate,
    InspectionTemplateRevision,
    MRBDisposition,
    MRBDispositionType,
    ParameterType,
    Part,
    RevisionStatus,
    TemplateType,
    ThresholdType,
    validate_defect_photo_file,
)
from .pdf_generator import generate_coc_pdf


@login_required
def template_list(request):
    type_filter = request.GET.get('type')
    status_filter = request.GET.get('status')

    templates = InspectionTemplate.objects.select_related('part').prefetch_related('revisions').all()

    if type_filter:
        templates = templates.filter(template_type=type_filter)

    enriched = []
    for tpl in templates:
        rev = tpl.get_latest_revision()
        if status_filter and rev and rev.status != status_filter:
            continue
        enriched.append({
            'template': tpl,
            'latest_rev': rev,
            'approved_rev': tpl.get_approved_revision(),
        })

    return render(request, 'quality/template_list.html', {
        'templates': enriched,
        'template_types': TemplateType.choices,
        'revision_statuses': RevisionStatus.choices,
        'selected_type': type_filter,
        'selected_status': status_filter,
    })


@login_required
def template_detail(request, pk):
    template = get_object_or_404(InspectionTemplate.objects.select_related('part'), pk=pk)
    
    # Active revision can be passed via ?rev=, else defaults to latest
    rev_id = request.GET.get('rev')
    if rev_id:
        revision = get_object_or_404(template.revisions, pk=rev_id)
    else:
        revision = template.get_latest_revision()

    parameters = []
    blueprints = []
    pins = []
    if revision:
        parameters = revision.parameters.select_related('pin').all()
        blueprints = revision.blueprints.all()
        if blueprints.exists():
            pins = BlueprintPin.objects.filter(blueprint__in=blueprints).select_related('parameter')

    return render(request, 'quality/template_detail.html', {
        'template': template,
        'revision': revision,
        'parameters': parameters,
        'blueprints': blueprints,
        'pins': pins,
        'parameter_types': ParameterType.choices,
        'threshold_types': ThresholdType.choices,
    })


@login_required
@role_required(UserRole.QUALITY_ENGINEER, UserRole.QUALITY_MANAGER, UserRole.PLANT_MANAGER)
def template_create(request):
    if request.method == 'POST':
        part_id = request.POST.get('part')
        template_type = request.POST.get('template_type', TemplateType.FINAL_PDI)
        title = request.POST.get('title', '').strip()
        template_code = request.POST.get('template_code', '').strip().upper()
        revision_label = request.POST.get('revision_label', 'Rev A').strip()

        part = get_object_or_404(Part, pk=part_id)

        try:
            tpl = InspectionTemplate.objects.create(
                part=part,
                template_type=template_type,
                title=title,
                template_code=template_code,
            )

            rev = InspectionTemplateRevision.objects.create(
                template=tpl,
                revision_label=revision_label,
                status=RevisionStatus.DRAFT,
                created_by=request.user,
            )

            AuditLog.log(
                action=AuditLog.ActionType.TEMPLATE_CREATED,
                user=request.user,
                request=request,
                model_name='InspectionTemplate',
                object_id=str(tpl.id),
                object_repr=tpl.template_code,
                new_value={'code': tpl.template_code, 'rev': rev.revision_label, 'part': part.part_number},
                details=f"Inspection template {tpl.template_code} [{rev.revision_label}] created for part {part.part_number} by {request.user.employee_id}."
            )

            messages.success(request, f"Template '{tpl.template_code}' created. You may now add inspection parameters and blueprints.")
            return redirect('quality:template_detail', pk=tpl.pk)

        except Exception as e:
            messages.error(request, f"Error creating template: {str(e)}")

    return render(request, 'quality/template_form.html', {
        'parts': Part.objects.filter(is_active=True),
        'template_types': TemplateType.choices,
    })


@login_required
@role_required(UserRole.QUALITY_ENGINEER, UserRole.QUALITY_MANAGER, UserRole.PLANT_MANAGER)
def parameter_create(request, revision_id):
    revision = get_object_or_404(InspectionTemplateRevision, pk=revision_id)
    
    if revision.is_locked:
        messages.error(request, f"Template revision [{revision.revision_label}] is locked and cannot be modified.")
        return redirect('quality:template_detail', pk=revision.template.pk)

    if request.method == 'POST':
        parameter_name = request.POST.get('parameter_name', '').strip()
        parameter_type = request.POST.get('parameter_type', ParameterType.DIMENSION)
        nominal_str = request.POST.get('nominal_value', '').strip()
        upper_str = request.POST.get('upper_tolerance', '').strip()
        lower_str = request.POST.get('lower_tolerance', '').strip()
        threshold_type = request.POST.get('threshold_type') or None
        threshold_str = request.POST.get('threshold_limit', '').strip()
        unit = request.POST.get('unit', 'mm').strip()
        is_ctq = request.POST.get('is_ctq') == 'on'
        required_tool_type = request.POST.get('required_tool_type', 'CALIPER')
        order = revision.parameters.count() + 1

        try:
            param = InspectionParameter.objects.create(
                template_revision=revision,
                parameter_name=parameter_name,
                parameter_type=parameter_type,
                nominal_value=Decimal(nominal_str) if nominal_str else None,
                upper_tolerance=Decimal(upper_str) if upper_str else None,
                lower_tolerance=Decimal(lower_str) if lower_str else None,
                threshold_type=threshold_type,
                threshold_limit=Decimal(threshold_str) if threshold_str else None,
                unit=unit,
                is_ctq=is_ctq,
                required_tool_type=required_tool_type,
                sequence_order=order,
            )

            messages.success(request, f"Inspection parameter '{param.parameter_name}' added.")
            return redirect('quality:template_detail', pk=revision.template.pk)

        except Exception as e:
            messages.error(request, f"Error saving parameter: {str(e)}")

    return redirect('quality:template_detail', pk=revision.template.pk)


@login_required
@role_required(UserRole.QUALITY_ENGINEER, UserRole.QUALITY_MANAGER, UserRole.PLANT_MANAGER)
def blueprint_upload(request, revision_id):
    revision = get_object_or_404(InspectionTemplateRevision, pk=revision_id)

    if revision.is_locked:
        messages.error(request, "Approved templates are locked from blueprint alterations.")
        return redirect('quality:template_detail', pk=revision.template.pk)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip() or f"{revision.template.part.part_number} Blueprint"
        drawing_file = request.FILES.get('drawing_file')

        if not drawing_file:
            messages.error(request, "Please attach a blueprint file.")
            return redirect('quality:template_detail', pk=revision.template.pk)

        bp = Blueprint.objects.create(
            template_revision=revision,
            title=title,
            drawing_file=drawing_file,
        )
        messages.success(request, f"Blueprint '{bp.title}' uploaded successfully. You can now place interactive inspection pins.")

    return redirect('quality:template_detail', pk=revision.template.pk)


@login_required
@role_required(UserRole.QUALITY_ENGINEER, UserRole.QUALITY_MANAGER, UserRole.PLANT_MANAGER)
def blueprint_pin_api(request, blueprint_id):
    """
    POST API to drop or update an interactive coordinate pin on an uploaded blueprint.
    Stores normalized X/Y coordinates (0.0 to 1.0).
    """
    blueprint = get_object_or_404(Blueprint, pk=blueprint_id)
    if blueprint.template_revision.is_locked:
        return JsonResponse({'success': False, 'error': 'Approved revisions are locked from pin modifications.'}, status=403)

    if request.method == 'POST':
        try:
            param_id = request.POST.get('parameter_id')
            label = request.POST.get('label', '').strip()
            coord_x = Decimal(str(request.POST.get('coord_x')))
            coord_y = Decimal(str(request.POST.get('coord_y')))

            param = None
            if param_id:
                param = get_object_or_404(InspectionParameter, pk=param_id, template_revision=blueprint.template_revision)

            pin_num = blueprint.pins.count() + 1
            if not label and param:
                label = f"Pin {pin_num} - {param.parameter_name}"

            pin, created = BlueprintPin.objects.update_or_create(
                blueprint=blueprint,
                parameter=param,
                defaults={
                    'pin_number': pin_num,
                    'label': label or f"Pin {pin_num}",
                    'coordinate_x': coord_x,
                    'coordinate_y': coord_y,
                }
            )

            AuditLog.log(
                action=AuditLog.ActionType.BLUEPRINT_PINNED,
                user=request.user,
                request=request,
                model_name='BlueprintPin',
                object_id=str(pin.id),
                object_repr=pin.label,
                details=f"Pin {pin.pin_number} placed at ({coord_x:.2%}, {coord_y:.2%}) on blueprint '{blueprint.title}'."
            )

            return JsonResponse({
                'success': True,
                'pin_id': pin.id,
                'pin_number': pin.pin_number,
                'label': pin.label,
                'coord_x': float(pin.coordinate_x),
                'coord_y': float(pin.coordinate_y),
                'is_ctq': param.is_ctq if param else False,
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'success': False, 'error': 'POST method required.'}, status=405)


@login_required
@role_required(UserRole.QUALITY_MANAGER, UserRole.PLANT_MANAGER)
def template_revision_approve(request, revision_id):
    """
    Quality Manager approval gate (BRD Section 4.1).
    Formally releases template revision to shopfloor production.
    """
    revision = get_object_or_404(InspectionTemplateRevision, pk=revision_id)

    if request.method == 'POST':
        notes = request.POST.get('approval_notes', '').strip()
        try:
            revision.approve(request.user, notes=notes)

            AuditLog.log(
                action=AuditLog.ActionType.TEMPLATE_APPROVED,
                user=request.user,
                request=request,
                model_name='InspectionTemplateRevision',
                object_id=str(revision.id),
                object_repr=f"{revision.template.template_code} [{revision.revision_label}]",
                details=f"Template revision {revision.template.template_code} [{revision.revision_label}] approved for production release by {request.user.employee_id}."
            )

            messages.success(request, f"Revision [{revision.revision_label}] approved and activated for production!")
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, 'message') else e))

    return redirect('quality:template_detail', pk=revision.template.pk)


# --------------------------------------------------------------------------
# PHASE 4: FLOOR INSPECTOR WORKFLOW, DUAL QR SCANNING & SUPERVISOR REVIEWS
# --------------------------------------------------------------------------

@login_required
@role_required(UserRole.QA_FLOOR_INSPECTOR, UserRole.QUALITY_ENGINEER, UserRole.PLANT_MANAGER)
def floor_scan_view(request):
    """
    Touch-friendly dual QR/barcode scanner landing portal (BRD Section 5.1).
    Supports live camera scanning with a clearly labeled demo/manual fallback.
    """
    workstations = Workstation.objects.filter(is_active=True).select_related('department')
    active_travelers = JobTraveler.objects.filter(status=JobTravelerStatus.ACTIVE).select_related(
        'work_order', 'work_order__part', 'work_order__raw_material_lot'
    )

    return render(request, 'quality/floor_scan.html', {
        'workstations': workstations,
        'travelers': active_travelers,
    })


@login_required
@role_required(UserRole.QA_FLOOR_INSPECTOR, UserRole.QUALITY_ENGINEER, UserRole.PLANT_MANAGER)
def floor_scan_validate(request):
    """
    Server-side verification of dual scanned codes (BRD Section 5.1).
    Validates workstation QR, traveler barcode, assigned operation, machine PM, and process hold timers.
    """
    if request.method != 'POST':
        return redirect('quality:floor_scan')

    station_code = request.POST.get('station_code', '').strip()
    traveler_code = request.POST.get('traveler_code', '').strip()
    is_demo = request.POST.get('is_demo') == 'true'

    if not station_code or not traveler_code:
        messages.error(request, "Both Station QR Code and Job Traveler Barcode are required.")
        return redirect('quality:floor_scan')

    # 1. Lookup Workstation
    workstation = Workstation.objects.filter(
        models.Q(qr_code_identifier__iexact=station_code) | models.Q(machine_code__iexact=station_code)
    ).first()

    if not workstation:
        AuditLog.log(
            action=AuditLog.ActionType.SECURITY_ALERT,
            user=request.user,
            request=request,
            model_name='Workstation',
            object_id='UNKNOWN',
            object_repr=station_code,
            details=f"Invalid Workstation QR scan attempt '{station_code}' by {request.user.employee_id}."
        )
        messages.error(request, f"Unrecognized Station QR code: '{station_code}'. Check physical machine plate.")
        return redirect('quality:floor_scan')

    # 2. Check Workstation Daily PM Lockout (BRD Section 2.2)
    can_ws_start, ws_reason = workstation.can_start_job()
    if not can_ws_start:
        AuditLog.log(
            action=AuditLog.ActionType.PM_LOCKOUT,
            user=request.user,
            request=request,
            model_name='Workstation',
            object_id=str(workstation.id),
            object_repr=workstation.machine_code,
            details=f"Inspection scan blocked on {workstation.machine_code}: {ws_reason}"
        )
        messages.error(request, f"Workstation Lockout: {ws_reason}")
        return redirect('quality:floor_scan')

    # 3. Lookup Job Traveler
    traveler = JobTraveler.objects.filter(
        models.Q(traveler_barcode__iexact=traveler_code) | models.Q(work_order__work_order_number__iexact=traveler_code)
    ).select_related('work_order', 'work_order__part').first()

    if not traveler:
        AuditLog.log(
            action=AuditLog.ActionType.SECURITY_ALERT,
            user=request.user,
            request=request,
            model_name='JobTraveler',
            object_id='UNKNOWN',
            object_repr=traveler_code,
            details=f"Invalid Job Traveler scan attempt '{traveler_code}' by {request.user.employee_id}."
        )
        messages.error(request, f"Unrecognized Job Traveler barcode: '{traveler_code}'.")
        return redirect('quality:floor_scan')

    if traveler.status == JobTravelerStatus.QUARANTINED:
        messages.error(request, f"Lot Quarantined: Job Traveler '{traveler.traveler_barcode}' is under quality quarantine hold.")
        return redirect('quality:floor_scan')

    if traveler.status == JobTravelerStatus.COMPLETED:
        messages.warning(request, f"Traveler '{traveler.traveler_barcode}' has already completed all production operations.")
        return redirect('quality:floor_scan')

    # 4. Find the matching operation on this traveler
    active_op = traveler.get_current_operation()
    if not active_op:
        messages.error(request, f"No pending operations found on traveler '{traveler.traveler_barcode}'.")
        return redirect('quality:floor_scan')

    # Verify that the scanned workstation matches the operation's assigned workstation
    if active_op.workstation != workstation:
        AuditLog.log(
            action=AuditLog.ActionType.SECURITY_ALERT,
            user=request.user,
            request=request,
            model_name='TravelerOperation',
            object_id=str(active_op.id),
            object_repr=f"Op {active_op.operation_sequence}",
            details=f"Workstation Mismatch: Traveler {traveler.traveler_barcode} active Op {active_op.operation_sequence} requires machine {active_op.workstation.machine_code}, but inspector scanned {workstation.machine_code}."
        )
        messages.error(
            request,
            f"Workstation Mismatch: Traveler {traveler.traveler_barcode} active step is 'Op {active_op.operation_sequence}: {active_op.operation_name}' "
            f"assigned to machine [{active_op.workstation.machine_code}], but you scanned [{workstation.machine_code}]."
        )
        return redirect('quality:floor_scan')

    # 5. Check Sequential Routing & Process Holds (BRD Section 7.1 & 8.2)
    can_start, start_reason = active_op.can_start()
    if not can_start:
        messages.error(request, f"Routing Interlock: {start_reason}")
        return redirect('quality:floor_scan')

    # 6. Ensure Operation has an Inspection Checklist Revision
    if not active_op.inspection_template_revision:
        pdi_template = InspectionTemplate.objects.filter(part=traveler.work_order.part).first()
        if pdi_template:
            rev = pdi_template.get_approved_revision() or pdi_template.get_latest_revision()
            if rev:
                active_op.inspection_template_revision = rev
                active_op.save(update_fields=['inspection_template_revision'])

    if not active_op.inspection_template_revision:
        messages.error(
            request,
            f"Checklist Missing: No inspection checklist revision is assigned to Op {active_op.operation_sequence} "
            f"for part {traveler.work_order.part.part_number}. Quality Manager must approve a template first."
        )
        return redirect('quality:floor_scan')

    # Save verified scan session
    request.session['verified_scan'] = {
        'station_id': workstation.id,
        'traveler_id': traveler.id,
        'op_id': active_op.id,
        'station_code': station_code,
        'traveler_code': traveler_code,
        'is_demo': is_demo,
        'timestamp': timezone.now().isoformat(),
    }

    return redirect('quality:floor_inspect', op_id=active_op.id)


@login_required
@role_required(UserRole.QA_FLOOR_INSPECTOR, UserRole.QUALITY_ENGINEER, UserRole.PLANT_MANAGER)
def floor_inspect_view(request, op_id):
    """
    Touch-friendly tablet inspection execution view (BRD Section 5.1 & 5.4).
    Captures measurements, validates tool calibrations, and enforces mandatory defect photos.
    """
    operation = get_object_or_404(
        TravelerOperation.objects.select_related(
            'traveler', 'traveler__work_order', 'traveler__work_order__part',
            'traveler__work_order__raw_material_lot', 'workstation', 'inspection_template_revision',
            'inspection_template_revision__template'
        ),
        pk=op_id
    )

    revision = operation.inspection_template_revision
    if not revision:
        messages.error(request, "Operation does not have an active inspection template revision.")
        return redirect('production:traveler_detail', pk=operation.traveler.pk)

    # Prevent duplicate active submissions
    active_inspection = FloorInspection.objects.filter(
        traveler_operation=operation,
        status__in=[FloorInspectionStatus.PENDING_REVIEW, FloorInspectionStatus.APPROVED, FloorInspectionStatus.CONCESSION_APPROVED]
    ).first()
    if active_inspection and request.method == 'POST':
        messages.warning(
            request,
            f"Operation '{operation.operation_name}' already has an active inspection ({active_inspection.inspection_number} - {active_inspection.get_status_display()})."
        )
        if request.user.can_review_inspections:
            return redirect('quality:supervisor_queue')
        return redirect('quality:floor_scan')

    parameters = revision.parameters.select_related('pin').all()
    blueprints = revision.blueprints.all()
    pins = BlueprintPin.objects.filter(blueprint__in=blueprints).select_related('parameter') if blueprints.exists() else []

    tools = InspectionTool.objects.all()

    if request.method == 'POST':
        scan_data = request.session.get('verified_scan', {})
        station_qr = scan_data.get('station_code', operation.workstation.qr_code_identifier)
        traveler_barcode = scan_data.get('traveler_code', operation.traveler.traveler_barcode)
        is_demo = scan_data.get('is_demo', False)
        notes = request.POST.get('inspector_notes', '').strip()

        try:
            with transaction.atomic():
                inspection_num = f"INSP-{timezone.now().year}-{FloorInspection.objects.count() + 1:04d}"
                inspection = FloorInspection.objects.create(
                    inspection_number=inspection_num,
                    traveler_operation=operation,
                    template_revision=revision,
                    workstation=operation.workstation,
                    inspector=request.user,
                    station_qr_scanned=station_qr,
                    traveler_barcode_scanned=traveler_barcode,
                    is_demo_scan=is_demo,
                    inspector_notes=notes,
                    status=FloorInspectionStatus.PENDING_REVIEW,
                )

                has_tolerance_failure = False

                for param in parameters:
                    measured_val = None
                    visual_val = None

                    if param.parameter_type == ParameterType.VISUAL:
                        visual_raw = request.POST.get(f"param_{param.id}")
                        visual_val = (visual_raw == 'PASS')
                    else:
                        val_raw = request.POST.get(f"param_{param.id}", '').strip()
                        if val_raw:
                            try:
                                measured_val = Decimal(val_raw)
                            except Exception:
                                raise ValidationError(f"Invalid numeric reading '{val_raw}' for parameter '{param.parameter_name}'.")

                    # Check measuring tool calibration on the server
                    tool_id = request.POST.get(f"tool_{param.id}")
                    tool = None
                    if tool_id:
                        tool = get_object_or_404(InspectionTool, pk=tool_id)
                        # Server enforces tool calibration check before accepting reading!
                        tool.validate_for_measurement()

                    # Save measurement reading
                    meas = InspectionMeasurement.objects.create(
                        inspection=inspection,
                        parameter=param,
                        measuring_tool=tool,
                        measured_value=measured_val,
                        visual_passed=visual_val,
                    )

                    if not meas.is_in_tolerance:
                        has_tolerance_failure = True

                # Mandatory Defect Photo Rule (BRD Section 5.4):
                # If ANY dimension is out of tolerance, inspector must upload at least one defect photo.
                uploaded_photos = request.FILES.getlist('defect_photos')
                if has_tolerance_failure and not uploaded_photos:
                    raise ValidationError(
                        "Mandatory Defect Photo: At least one out-of-tolerance parameter was recorded. "
                        "BRD Section 5.4 requires uploading clear photographic evidence of the defect before the inspection can be submitted."
                    )

                for photo_file in uploaded_photos:
                    validate_defect_photo_file(photo_file)
                    InspectionDefectPhoto.objects.create(
                        inspection=inspection,
                        photo_file=photo_file,
                        caption=request.POST.get('photo_caption', 'Out of tolerance defect photo').strip(),
                    )

                # Recalculate tolerance and CTQ status directly from database
                inspection.recalculate_tolerance_and_ctq()

                AuditLog.log(
                    action=AuditLog.ActionType.INSPECTION_ENTRY,
                    user=request.user,
                    request=request,
                    model_name='FloorInspection',
                    object_id=str(inspection.id),
                    object_repr=inspection.inspection_number,
                    details=f"Floor inspection {inspection.inspection_number} logged for Op {operation.operation_sequence} by {request.user.employee_id}. Overall tolerance: {inspection.overall_in_tolerance}, CTQ failure: {inspection.has_ctq_defect}."
                )

                messages.success(
                    request,
                    f"Inspection '{inspection.inspection_number}' submitted successfully! Routed to Shift Supervisor approval queue."
                )
                if request.user.can_review_inspections:
                    return redirect('quality:supervisor_queue')
                return redirect('quality:floor_scan')

        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, 'message') else e))

    return render(request, 'quality/inspector_tablet.html', {
        'operation': operation,
        'revision': revision,
        'parameters': parameters,
        'blueprints': blueprints,
        'pins': pins,
        'tools': tools,
        'active_inspection': active_inspection,
    })


@login_required
@role_required(UserRole.SHIFT_SUPERVISOR, UserRole.QUALITY_MANAGER, UserRole.PLANT_MANAGER)
def supervisor_queue_view(request):
    """
    Shift Supervisor and Quality Manager live approval queue (BRD Section 6.1).
    """
    status_filter = request.GET.get('status', FloorInspectionStatus.PENDING_REVIEW)
    inspections = FloorInspection.objects.select_related(
        'traveler_operation', 'traveler_operation__traveler', 'traveler_operation__traveler__work_order',
        'traveler_operation__traveler__work_order__part', 'workstation', 'inspector', 'template_revision'
    ).prefetch_related('measurements', 'defect_photos')

    if status_filter:
        inspections = inspections.filter(status=status_filter)

    return render(request, 'quality/supervisor_review_queue.html', {
        'inspections': inspections,
        'statuses': FloorInspectionStatus.choices,
        'selected_status': status_filter,
    })


@login_required
@role_required(UserRole.SHIFT_SUPERVISOR, UserRole.QUALITY_MANAGER, UserRole.PLANT_MANAGER)
def supervisor_review_view(request, inspection_id):
    """
    Detailed inspection review portal with Approve, Concession, and Reject workflows.
    Enforces the Zero-Concession rule on CTQ parameters.
    """
    inspection = get_object_or_404(
        FloorInspection.objects.select_related(
            'traveler_operation', 'traveler_operation__traveler', 'traveler_operation__traveler__work_order',
            'traveler_operation__traveler__work_order__part', 'workstation', 'inspector', 'template_revision',
            'reviewed_by'
        ),
        pk=inspection_id
    )

    measurements = inspection.measurements.select_related('parameter', 'measuring_tool').all()
    defect_photos = inspection.defect_photos.all()
    concession = getattr(inspection, 'concession_record', None)

    if request.method == 'POST':
        action = request.POST.get('action')

        try:
            if action == 'approve':
                notes = request.POST.get('notes', '').strip()
                inspection.approve(request.user, notes=notes, request=request)
                messages.success(request, f"Inspection '{inspection.inspection_number}' approved. Operation cleared for downstream production.")
                return redirect('quality:supervisor_queue')

            elif action == 'concession':
                reason_code = request.POST.get('reason_code', ConcessionReason.ENGINEERING_DEVIATION)
                justification = request.POST.get('engineering_justification', '').strip()

                if not justification:
                    messages.error(request, "A detailed engineering justification is mandatory when issuing a concession.")
                    return redirect('quality:supervisor_review', inspection_id=inspection.id)

                # Server-side validation of Zero-Concession rule
                inspection.grant_concession(request.user, reason_code=reason_code, justification=justification, request=request)
                messages.success(request, f"Concession granted for '{inspection.inspection_number}'. Batch released under engineering waiver.")
                return redirect('quality:supervisor_queue')

            elif action == 'reject':
                reason = request.POST.get('rejection_reason', '').strip()
                if not reason:
                    messages.error(request, "Rejection reason is required.")
                    return redirect('quality:supervisor_review', inspection_id=inspection.id)

                inspection.reject_and_quarantine(request.user, reason=reason, request=request)
                messages.warning(
                    request,
                    f"Inspection '{inspection.inspection_number}' REJECTED. Job Traveler '{inspection.traveler_operation.traveler.traveler_barcode}' has been quarantined."
                )
                return redirect('quality:supervisor_queue')

        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, 'message') else e))

    return render(request, 'quality/supervisor_review_detail.html', {
        'inspection': inspection,
        'measurements': measurements,
        'defect_photos': defect_photos,
        'concession': concession,
        'concession_reasons': ConcessionReason.choices,
    })


# --------------------------------------------------------------------------
# PHASE 5A: PRE-DISPATCH INSPECTION (PDI) WORKFLOW & INTERLOCKS
# --------------------------------------------------------------------------

@login_required
@role_required(UserRole.QA_FLOOR_INSPECTOR, UserRole.QUALITY_ENGINEER, UserRole.SHIFT_SUPERVISOR, UserRole.QUALITY_MANAGER, UserRole.PLANT_MANAGER)
def pdi_queue_view(request):
    """
    Central Pre-Dispatch Inspection (PDI) staging portal conforming to BRD Section 10.1.
    Displays travelers categorized by PDI readiness, sequential interlocks, and quality clearance.
    """
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('stage', '')

    travelers = JobTraveler.objects.select_related(
        'work_order', 'work_order__part', 'work_order__raw_material_lot'
    ).prefetch_related(
        'operations', 'operations__inspections', 'operations__workstation'
    ).order_by('-created_at')

    if search_query:
        travelers = travelers.filter(
            models.Q(traveler_barcode__icontains=search_query) |
            models.Q(work_order__work_order_number__icontains=search_query) |
            models.Q(work_order__part__part_number__icontains=search_query)
        )

    pdi_items = []
    counts = {'all': 0, 'ready': 0, 'in_review': 0, 'cleared': 0, 'locked': 0, 'quarantined': 0}

    for traveler in travelers:
        pdi_op = traveler.get_pdi_operation()
        is_ready, ready_reason = traveler.is_ready_for_pdi()
        pdi_insp = traveler.get_pdi_inspection()
        is_pdi_approved = traveler.is_pdi_approved()

        if traveler.status == JobTravelerStatus.QUARANTINED:
            stage = 'quarantined'
            badge_class = 'danger'
            stage_display = 'Quarantined / Defect Hold'
            stage_desc = ready_reason
        elif is_pdi_approved:
            stage = 'cleared'
            badge_class = 'success'
            stage_display = 'PDI Approved & Cleared'
            stage_desc = f"Cleared under inspection {pdi_insp.inspection_number}" if pdi_insp else "Approved"
        elif pdi_insp and pdi_insp.status == FloorInspectionStatus.PENDING_REVIEW:
            stage = 'in_review'
            badge_class = 'warning text-dark'
            stage_display = 'Awaiting Quality Sign-off'
            stage_desc = f"{pdi_insp.inspection_number} submitted by {pdi_insp.inspector.employee_id}"
        elif is_ready:
            stage = 'ready'
            badge_class = 'info text-dark'
            stage_display = 'Ready for Final PDI'
            stage_desc = 'All preliminary machining and process holds completed.'
        else:
            stage = 'locked'
            badge_class = 'secondary'
            stage_display = 'Routing Locked'
            stage_desc = ready_reason

        counts['all'] += 1
        if stage in counts:
            counts[stage] += 1

        if not status_filter or status_filter == stage:
            pdi_items.append({
                'traveler': traveler,
                'pdi_op': pdi_op,
                'pdi_insp': pdi_insp,
                'is_ready': is_ready,
                'ready_reason': ready_reason,
                'is_approved': is_pdi_approved,
                'stage': stage,
                'stage_display': stage_display,
                'stage_desc': stage_desc,
                'badge_class': badge_class,
            })

    return render(request, 'quality/pdi_queue.html', {
        'pdi_items': pdi_items,
        'counts': counts,
        'selected_stage': status_filter,
        'search_query': search_query,
    })


@login_required
@role_required(UserRole.QA_FLOOR_INSPECTOR, UserRole.QUALITY_ENGINEER, UserRole.PLANT_MANAGER)
def pdi_execute_view(request, traveler_id):
    """
    Direct launchpad for Final PDI execution.
    Enforces strict server-side pre-conditions:
    1. 100% of preceding operations completed.
    2. Cooling/process holds fully elapsed.
    3. Traveler not quarantined.
    """
    traveler = get_object_or_404(JobTraveler.objects.select_related('work_order', 'work_order__part'), pk=traveler_id)
    is_ready, ready_reason = traveler.is_ready_for_pdi()

    if not is_ready:
        AuditLog.log(
            action=AuditLog.ActionType.ROUTING_LOCKOUT,
            user=request.user,
            request=request,
            model_name='JobTraveler',
            object_id=str(traveler.id),
            object_repr=traveler.traveler_barcode,
            details=f"PDI Execution blocked for traveler {traveler.traveler_barcode}: {ready_reason}"
        )
        messages.error(request, f"PDI Gateway Lockout: {ready_reason}")
        return redirect('quality:pdi_queue')

    pdi_op = traveler.get_pdi_operation()
    if not pdi_op:
        messages.error(request, f"No designated PDI operation found on traveler '{traveler.traveler_barcode}'.")
        return redirect('quality:pdi_queue')

    # Prepare verified scan session for floor_inspect view
    request.session['verified_scan'] = {
        'station_id': pdi_op.workstation.id if pdi_op.workstation else None,
        'traveler_id': traveler.id,
        'op_id': pdi_op.id,
        'station_code': pdi_op.workstation.qr_code_identifier if pdi_op.workstation else 'PDI-STATION',
        'traveler_code': traveler.traveler_barcode,
        'is_demo': False,
        'timestamp': timezone.now().isoformat(),
    }

    return redirect('quality:floor_inspect', op_id=pdi_op.id)


@login_required
def coc_list_view(request):
    """
    List and filter all issued Certificates of Conformance.
    """
    status_filter = request.GET.get('status')
    search_query = request.GET.get('q', '').strip()

    certificates = CertificateOfConformance.objects.select_related(
        'traveler', 'work_order', 'work_order__part', 'work_order__raw_material_lot', 'issued_by'
    ).all()

    if status_filter:
        certificates = certificates.filter(status=status_filter)

    if search_query:
        certificates = certificates.filter(
            models.Q(certificate_number__icontains=search_query) |
            models.Q(traveler__traveler_barcode__icontains=search_query) |
            models.Q(work_order__work_order_number__icontains=search_query) |
            models.Q(work_order__part__part_number__icontains=search_query)
        )

    return render(request, 'quality/coc_list.html', {
        'certificates': certificates,
        'statuses': CertificateStatus.choices,
        'selected_status': status_filter,
        'search_query': search_query,
    })


@login_required
def coc_generate_view(request, traveler_id):
    """
    Server-authenticated Certificate of Conformance issuance workflow.
    Conforms to BRD Section 11.1 & 11.2.
    """
    # 1. Role-based Access Control
    if not request.user.can_issue_coc:
        AuditLog.log(
            action=AuditLog.ActionType.SECURITY_ALERT,
            user=request.user,
            request=request,
            model_name='CertificateOfConformance',
            object_id=str(traveler_id),
            object_repr=f"Traveler ID {traveler_id}",
            details=f"User {request.user.employee_id} ({request.user.role}) denied permission to generate Certificate of Conformance."
        )
        messages.error(request, "Permission Denied: Only Quality Managers, Quality Engineers, or Plant Managers can issue Certificates of Conformance.")
        return redirect('quality:pdi_queue')

    traveler = get_object_or_404(
        JobTraveler.objects.select_related(
            'work_order', 'work_order__part', 'work_order__raw_material_lot', 'work_order__raw_material_lot__material_grade'
        ),
        pk=traveler_id
    )

    # 2. Server-side eligibility validation
    is_eligible, reasons = CertificateOfConformance.validate_eligibility(traveler)
    if not is_eligible:
        reason_msg = "; ".join(reasons)
        AuditLog.log(
            action=AuditLog.ActionType.SHIPPING_INTERLOCK,
            user=request.user,
            request=request,
            model_name='JobTraveler',
            object_id=str(traveler.id),
            object_repr=traveler.traveler_barcode,
            details=f"CoC Generation rejected for traveler {traveler.traveler_barcode}: {reason_msg}"
        )
        messages.error(request, f"CoC Eligibility Lockout: {reason_msg}")
        return redirect('quality:pdi_queue')

    # 3. Check for existing active certificate
    existing = CertificateOfConformance.objects.filter(
        traveler=traveler,
        status=CertificateStatus.ACTIVE
    ).first()

    if existing:
        if request.method == 'POST' and request.POST.get('reissue') == 'true':
            reason = request.POST.get('reissue_reason', '').strip()
            if not reason:
                messages.error(request, "Reissue Rejected: An engineering justification is mandatory when superseding an existing certificate.")
                return redirect('quality:coc_detail', coc_id=existing.id)

            with transaction.atomic():
                next_ver = existing.version + 1
                new_cert_num = f"COC-{traveler.work_order.work_order_number}-v{next_ver}"
                if CertificateOfConformance.objects.filter(certificate_number=new_cert_num).exists():
                    new_cert_num = f"COC-{traveler.work_order.work_order_number}-v{next_ver}-{int(timezone.now().timestamp())}"

                new_coc = CertificateOfConformance(
                    certificate_number=new_cert_num,
                    traveler=traveler,
                    work_order=traveler.work_order,
                    status=CertificateStatus.ACTIVE,
                    version=next_ver,
                    issued_by=request.user,
                    issued_at=timezone.now(),
                    reissue_reason=reason,
                )
                new_coc.save()

                existing.status = CertificateStatus.SUPERSEDED
                existing.superseded_by = new_coc
                existing.save(update_fields=['status', 'superseded_by'])

                pdf_bytes = generate_coc_pdf(new_coc, request=request)
                sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()
                new_coc.pdf_sha256_hash = sha256_hash
                new_coc.pdf_file.save(f"{new_coc.certificate_number}.pdf", ContentFile(pdf_bytes), save=False)
                new_coc.save(update_fields=['pdf_sha256_hash', 'pdf_file'])

                AuditLog.log(
                    action=AuditLog.ActionType.COC_REISSUED,
                    user=request.user,
                    request=request,
                    model_name='CertificateOfConformance',
                    object_id=str(new_coc.id),
                    object_repr=new_coc.certificate_number,
                    details=f"Certificate of Conformance reissued as {new_coc.certificate_number} (v{next_ver}) for traveler {traveler.traveler_barcode}. Previous certificate {existing.certificate_number} superseded. Justification: {reason}"
                )
                messages.success(request, f"Certificate of Conformance {new_coc.certificate_number} (v{next_ver}) issued successfully. Previous certificate superseded.")
                return redirect('quality:coc_detail', coc_id=new_coc.id)
        else:
            messages.warning(request, f"Active Certificate {existing.certificate_number} already exists for this traveler. Use the Reissue function to supersede if changes are needed.")
            return redirect('quality:coc_detail', coc_id=existing.id)

    # 4. Handle initial CoC generation
    if request.method == 'POST':
        with transaction.atomic():
            next_ver = 1
            new_cert_num = f"COC-{traveler.work_order.work_order_number}"
            if CertificateOfConformance.objects.filter(certificate_number=new_cert_num).exists():
                new_cert_num = f"COC-{traveler.work_order.work_order_number}-{int(timezone.now().timestamp())}"

            coc = CertificateOfConformance(
                certificate_number=new_cert_num,
                traveler=traveler,
                work_order=traveler.work_order,
                status=CertificateStatus.ACTIVE,
                version=next_ver,
                issued_by=request.user,
                issued_at=timezone.now(),
                notes=request.POST.get('notes', '').strip(),
            )
            coc.save()

            pdf_bytes = generate_coc_pdf(coc, request=request)
            sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()
            coc.pdf_sha256_hash = sha256_hash
            coc.pdf_file.save(f"{coc.certificate_number}.pdf", ContentFile(pdf_bytes), save=False)
            coc.save(update_fields=['pdf_sha256_hash', 'pdf_file'])

            AuditLog.log(
                action=AuditLog.ActionType.COC_GENERATED,
                user=request.user,
                request=request,
                model_name='CertificateOfConformance',
                object_id=str(coc.id),
                object_repr=coc.certificate_number,
                details=f"Certificate of Conformance {coc.certificate_number} generated for traveler {traveler.traveler_barcode}. SHA-256 Digest: {sha256_hash}"
            )
            messages.success(request, f"Certificate of Conformance {coc.certificate_number} issued and authenticated successfully.")
            return redirect('quality:coc_detail', coc_id=coc.id)

    # GET: Confirmation / review before generation
    pdi_insp = traveler.get_pdi_inspection()
    return render(request, 'quality/coc_generate.html', {
        'traveler': traveler,
        'work_order': traveler.work_order,
        'part': traveler.work_order.part,
        'lot': traveler.work_order.raw_material_lot,
        'pdi_insp': pdi_insp,
    })


@login_required
def coc_detail_view(request, coc_id):
    """
    Printable HTML document viewer for a Certificate of Conformance.
    Provides @media print formatting and buttons for PDF download & reissuance.
    """
    coc = get_object_or_404(
        CertificateOfConformance.objects.select_related(
            'traveler',
            'work_order',
            'work_order__part',
            'work_order__part__material_grade',
            'work_order__raw_material_lot',
            'work_order__raw_material_lot__material_grade',
            'work_order__raw_material_lot__mtc_verified_by',
            'issued_by',
            'superseded_by',
        ),
        pk=coc_id
    )

    pdi_insp = coc.traveler.get_pdi_inspection()
    measurements = pdi_insp.measurements.select_related('parameter', 'measuring_tool').all() if pdi_insp else []

    # Get verification URL
    domain = request.get_host()
    verify_url = f"{request.scheme}://{domain}/quality/coc/verify/{coc.verification_token}/"

    return render(request, 'quality/coc_document.html', {
        'coc': coc,
        'traveler': coc.traveler,
        'work_order': coc.work_order,
        'part': coc.work_order.part,
        'lot': coc.work_order.raw_material_lot,
        'pdi_insp': pdi_insp,
        'measurements': measurements,
        'verify_url': verify_url,
    })


@login_required
def coc_download_view(request, coc_id):
    """
    Secure PDF download endpoint.
    Re-validates traveler quarantine status dynamically before delivering the binary file.
    """
    coc = get_object_or_404(
        CertificateOfConformance.objects.select_related('traveler', 'work_order'),
        pk=coc_id
    )

    # Server-side Revalidation: Block download if batch has been quarantined since CoC issuance
    if coc.traveler.status == JobTravelerStatus.QUARANTINED:
        AuditLog.log(
            action=AuditLog.ActionType.SECURITY_ALERT,
            user=request.user,
            request=request,
            model_name='CertificateOfConformance',
            object_id=str(coc.id),
            object_repr=coc.certificate_number,
            details=f"CoC PDF download blocked for certificate {coc.certificate_number}: traveler {coc.traveler.traveler_barcode} is quarantined."
        )
        messages.error(request, "Security Lockout: This Job Traveler has been placed under Quality Quarantine. Certificate PDF download is locked.")
        return redirect('quality:coc_detail', coc_id=coc.id)

    # Ensure PDF exists; generate on-demand if missing
    if not coc.pdf_file:
        pdf_bytes = generate_coc_pdf(coc, request=request)
        sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()
        coc.pdf_sha256_hash = sha256_hash
        coc.pdf_file.save(f"{coc.certificate_number}.pdf", ContentFile(pdf_bytes), save=False)
        coc.save(update_fields=['pdf_sha256_hash', 'pdf_file'])

    return FileResponse(
        coc.pdf_file.open('rb'),
        content_type='application/pdf',
        as_attachment=True,
        filename=f"{coc.certificate_number}.pdf"
    )


def coc_verify_view(request, token):
    """
    Public customer QR/URL verification endpoint.
    Displays verified certificate attributes without disclosing private company data,
    audit logs, employee passwords, or internal manufacturing margins.
    """
    coc = CertificateOfConformance.objects.select_related(
        'traveler',
        'work_order',
        'work_order__part',
        'work_order__raw_material_lot',
        'work_order__raw_material_lot__material_grade',
        'issued_by'
    ).filter(verification_token=token).first()

    if not coc:
        return render(request, 'quality/coc_verify.html', {
            'is_valid': False,
            'token': token,
        })

    pdi_insp = coc.traveler.get_pdi_inspection()

    return render(request, 'quality/coc_verify.html', {
        'is_valid': True,
        'coc': coc,
        'traveler': coc.traveler,
        'work_order': coc.work_order,
        'part': coc.work_order.part,
        'lot': coc.work_order.raw_material_lot,
        'pdi_insp': pdi_insp,
    })


@login_required
def mrb_queue_view(request):
    """
    Material Review Board (MRB) Live Quarantine Holding Queue.
    Conforms to BRD Section 6.3.
    Lists quarantined Job Travelers and Raw Material Intake lots awaiting MRB disposition.
    """
    quarantined_travelers = JobTraveler.objects.filter(
        status=JobTravelerStatus.QUARANTINED
    ).select_related('work_order', 'work_order__part', 'work_order__raw_material_lot')

    quarantined_lots = RawMaterialIntake.objects.filter(
        status=IntakeStatus.QUARANTINED
    ).select_related('material_grade')

    recent_dispositions = MRBDisposition.objects.select_related(
        'traveler', 'raw_material_lot', 'authorized_by'
    ).order_by('-authorized_at')[:20]

    return render(request, 'quality/mrb_queue.html', {
        'quarantined_travelers': quarantined_travelers,
        'quarantined_lots': quarantined_lots,
        'recent_dispositions': recent_dispositions,
    })


@login_required
def mrb_disposition_traveler_view(request, traveler_id):
    """
    Execute Material Review Board (MRB) disposition for a quarantined Job Traveler.
    Supports: REWORK, SCRAP, and CUSTOMER_CONCESSION.
    """
    if not request.user.can_mrb_disposition:
        AuditLog.log(
            action=AuditLog.ActionType.SECURITY_ALERT,
            user=request.user,
            request=request,
            model_name='MRBDisposition',
            object_id=str(traveler_id),
            object_repr=f"Traveler {traveler_id}",
            details=f"User {request.user.employee_id} denied access to execute MRB disposition."
        )
        messages.error(request, "Permission Denied: Only Quality Managers or Plant Managers can authorize MRB dispositions.")
        return redirect('quality:mrb_queue')

    traveler = get_object_or_404(
        JobTraveler.objects.select_related('work_order', 'work_order__part', 'work_order__raw_material_lot'),
        pk=traveler_id
    )

    if request.method == 'POST':
        disp_type = request.POST.get('disposition_type', '').strip()
        defect_desc = request.POST.get('defect_description', '').strip()
        eng_just = request.POST.get('engineering_justification', '').strip()
        rework_inst = request.POST.get('rework_instructions', '').strip()
        cost_code = request.POST.get('scrap_cost_code', '').strip()
        scrap_verified = request.POST.get('scrap_verified_at_bin') == 'on'
        customer_doc = request.FILES.get('customer_approval_doc')

        if not (disp_type and defect_desc and eng_just):
            messages.error(request, "Validation Error: Disposition Type, Defect Description, and Engineering Justification are mandatory.")
            return render(request, 'quality/mrb_form.html', {
                'target_type': 'traveler',
                'target': traveler,
                'disposition_types': MRBDispositionType.choices,
            })

        with transaction.atomic():
            disp_num = f"MRB-{traveler.traveler_barcode}-{int(timezone.now().timestamp())}"
            rework_trv = None

            if disp_type == MRBDispositionType.REWORK:
                # Generate dedicated Rework Work Order & Job Traveler per BRD Section 6.3
                rework_wo_num = f"WO-RWK-{traveler.work_order.work_order_number}"
                if WorkOrder.objects.filter(work_order_number=rework_wo_num).exists():
                    rework_wo_num = f"WO-RWK-{traveler.work_order.work_order_number}-{int(timezone.now().timestamp())}"

                rework_wo = WorkOrder.objects.create(
                    work_order_number=rework_wo_num,
                    part=traveler.work_order.part,
                    raw_material_lot=traveler.work_order.raw_material_lot,
                    target_quantity=traveler.work_order.target_quantity,
                    status=WorkOrderStatus.RELEASED,
                    released_by=request.user,
                    released_at=timezone.now(),
                )

                rework_barcode = f"RWK-{traveler.traveler_barcode}"
                if JobTraveler.objects.filter(traveler_barcode=rework_barcode).exists():
                    rework_barcode = f"RWK-{traveler.traveler_barcode}-{int(timezone.now().timestamp())}"

                rework_trv = JobTraveler.objects.create(
                    work_order=rework_wo,
                    traveler_barcode=rework_barcode,
                    current_operation_sequence=10,
                    status=JobTravelerStatus.ACTIVE
                )

            elif disp_type == MRBDispositionType.SCRAP:
                # Update scrapped quantity on production work order
                traveler.work_order.scrapped_quantity += traveler.work_order.target_quantity
                traveler.work_order.save(update_fields=['scrapped_quantity'])

            elif disp_type == MRBDispositionType.CUSTOMER_CONCESSION:
                if not customer_doc:
                    messages.error(request, "Documentation Error: Uploading formal customer written concession approval document is mandatory.")
                    return render(request, 'quality/mrb_form.html', {
                        'target_type': 'traveler',
                        'target': traveler,
                        'disposition_types': MRBDispositionType.choices,
                    })
                # Release quarantine hold under customer concession
                traveler.status = JobTravelerStatus.ACTIVE
                traveler.save(update_fields=['status'])

            disposition = MRBDisposition.objects.create(
                disposition_number=disp_num,
                traveler=traveler,
                disposition_type=disp_type,
                defect_description=defect_desc,
                engineering_justification=eng_just,
                rework_instructions=rework_inst,
                rework_traveler=rework_trv,
                scrap_cost_code=cost_code,
                scrap_verified_at_bin=scrap_verified,
                customer_approval_doc=customer_doc,
                authorized_by=request.user,
                authorized_at=timezone.now(),
            )

            AuditLog.log(
                action=AuditLog.ActionType.MRB_DISPOSITION,
                user=request.user,
                request=request,
                model_name='MRBDisposition',
                object_id=str(disposition.id),
                object_repr=disposition.disposition_number,
                details=f"MRB Disposition {disposition.disposition_number} ({disposition.get_disposition_type_display()}) authorized for traveler {traveler.traveler_barcode}."
            )

            messages.success(request, f"MRB Disposition {disposition.disposition_number} successfully recorded!")
            return redirect('quality:mrb_detail', disposition_id=disposition.id)

    return render(request, 'quality/mrb_form.html', {
        'target_type': 'traveler',
        'target': traveler,
        'disposition_types': MRBDispositionType.choices,
    })


@login_required
def mrb_disposition_lot_view(request, lot_id):
    """
    Execute Material Review Board (MRB) disposition for a quarantined Raw Material Intake lot.
    Supports: RTV (Return to Vendor) or SCRAP.
    """
    if not request.user.can_mrb_disposition:
        messages.error(request, "Permission Denied: Only Quality Managers or Plant Managers can authorize MRB dispositions.")
        return redirect('quality:mrb_queue')

    lot = get_object_or_404(RawMaterialIntake.objects.select_related('material_grade'), pk=lot_id)

    if request.method == 'POST':
        disp_type = request.POST.get('disposition_type', '').strip()
        defect_desc = request.POST.get('defect_description', '').strip()
        eng_just = request.POST.get('engineering_justification', '').strip()
        debit_note = request.POST.get('debit_note_number', '').strip()
        cost_code = request.POST.get('scrap_cost_code', '').strip()
        scrap_verified = request.POST.get('scrap_verified_at_bin') == 'on'

        with transaction.atomic():
            disp_num = f"MRB-RAW-{lot.lot_number}-{int(timezone.now().timestamp())}"

            disposition = MRBDisposition.objects.create(
                disposition_number=disp_num,
                raw_material_lot=lot,
                disposition_type=disp_type,
                defect_description=defect_desc,
                engineering_justification=eng_just,
                debit_note_number=debit_note,
                scrap_cost_code=cost_code,
                scrap_verified_at_bin=scrap_verified,
                authorized_by=request.user,
                authorized_at=timezone.now(),
            )

            AuditLog.log(
                action=AuditLog.ActionType.MRB_DISPOSITION,
                user=request.user,
                request=request,
                model_name='MRBDisposition',
                object_id=str(disposition.id),
                object_repr=disposition.disposition_number,
                details=f"MRB Disposition {disposition.disposition_number} ({disposition.get_disposition_type_display()}) authorized for raw material lot {lot.lot_number}."
            )

            messages.success(request, f"MRB Raw Material Disposition {disposition.disposition_number} logged successfully.")
            return redirect('quality:mrb_detail', disposition_id=disposition.id)

    return render(request, 'quality/mrb_form.html', {
        'target_type': 'lot',
        'target': lot,
        'disposition_types': [
            (MRBDispositionType.RTV, 'Return to Vendor (RTV Debit Note)'),
            (MRBDispositionType.SCRAP, 'Scrap Disposition & Write-Off'),
        ],
    })


@login_required
def mrb_detail_view(request, disposition_id):
    """
    Detailed permanent record of an authorized MRB disposition.
    """
    disposition = get_object_or_404(
        MRBDisposition.objects.select_related(
            'traveler',
            'traveler__work_order',
            'traveler__work_order__part',
            'raw_material_lot',
            'raw_material_lot__material_grade',
            'authorized_by',
            'rework_traveler',
        ),
        pk=disposition_id
    )

    return render(request, 'quality/mrb_detail.html', {
        'disposition': disposition,
    })


