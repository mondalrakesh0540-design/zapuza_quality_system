from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from apps.accounts.models import UserRole
from apps.accounts.permissions import role_required
from apps.audit_trail.models import AuditLog
from .models import (
    Department,
    InspectionTool,
    MachinePMLog,
    ShiftType,
    ToolStatus,
    ToolType,
    Workstation,
    WorkstationStatus,
)


@login_required
def workstation_list(request):
    department_id = request.GET.get('department')
    status_filter = request.GET.get('status')

    workstations = Workstation.objects.select_related('department').all()
    if department_id:
        workstations = workstations.filter(department_id=department_id)
    if status_filter:
        workstations = workstations.filter(status=status_filter)

    departments = Department.objects.filter(is_active=True)

    # Attach live clearance and PM status to each workstation
    enriched_workstations = []
    today = timezone.now().date()
    for ws in workstations:
        pm_log = ws.get_latest_pm_log(date=today)
        can_start, reason = ws.can_start_job(date=today)
        enriched_workstations.append({
            'ws': ws,
            'pm_log': pm_log,
            'can_start': can_start,
            'lockout_reason': reason if not can_start else None,
        })

    return render(request, 'master_data/workstation_list.html', {
        'workstations': enriched_workstations,
        'departments': departments,
        'selected_dept': department_id,
        'selected_status': status_filter,
        'today': today,
    })


@login_required
def workstation_detail(request, pk):
    workstation = get_object_or_404(Workstation.objects.select_related('department'), pk=pk)
    today = timezone.now().date()
    today_pm = workstation.get_latest_pm_log(date=today)
    can_start, lockout_reason = workstation.can_start_job(date=today)
    pm_history = workstation.pm_logs.select_related('completed_by').order_by('-log_date', '-created_at')[:15]

    return render(request, 'master_data/workstation_detail.html', {
        'workstation': workstation,
        'today': today,
        'today_pm': today_pm,
        'can_start': can_start,
        'lockout_reason': lockout_reason,
        'pm_history': pm_history,
    })


@login_required
@role_required(UserRole.SHIFT_SUPERVISOR, UserRole.QA_FLOOR_INSPECTOR, UserRole.PLANT_MANAGER)
def workstation_pm_create(request, pk):
    workstation = get_object_or_404(Workstation, pk=pk)
    today = timezone.now().date()

    if request.method == 'POST':
        shift = request.POST.get('shift', ShiftType.MORNING)
        zero_point_verified = request.POST.get('zero_point_verified') == 'on'
        lubrication_level_ok = request.POST.get('lubrication_level_ok') == 'on'
        safety_interlocks_ok = request.POST.get('safety_interlocks_ok') == 'on'
        spindle_runout_ok = request.POST.get('spindle_runout_ok') == 'on'
        pneumatic_pressure_ok = request.POST.get('pneumatic_pressure_ok') == 'on'
        emergency_stop_tested = request.POST.get('emergency_stop_tested') == 'on'
        remarks = request.POST.get('remarks', '').strip()

        # Update or create the PM log for this workstation, date, and shift
        pm_log, created = MachinePMLog.objects.get_or_create(
            workstation=workstation,
            log_date=today,
            shift=shift,
            defaults={'completed_by': request.user}
        )
        pm_log.completed_by = request.user
        pm_log.zero_point_verified = zero_point_verified
        pm_log.lubrication_level_ok = lubrication_level_ok
        pm_log.safety_interlocks_ok = safety_interlocks_ok
        pm_log.spindle_runout_ok = spindle_runout_ok
        pm_log.pneumatic_pressure_ok = pneumatic_pressure_ok
        pm_log.emergency_stop_tested = emergency_stop_tested
        pm_log.remarks = remarks
        pm_log.save()

        # Update workstation status if maintenance was locked
        if pm_log.is_passed:
            if workstation.status == WorkstationStatus.MAINTENANCE_LOCKED:
                workstation.status = WorkstationStatus.IDLE
                workstation.save(update_fields=['status'])

            AuditLog.log(
                action=AuditLog.ActionType.PM_SIGN_OFF,
                user=request.user,
                request=request,
                model_name='Workstation',
                object_id=str(workstation.id),
                object_repr=workstation.machine_code,
                new_value={'pm_status': 'PASSED', 'shift': shift, 'date': str(today)},
                details=f"Daily PM checklist PASSED for {workstation.machine_code} on {today} ({shift}) by {request.user.employee_id}."
            )
            messages.success(
                request,
                f"Daily PM Checklist successfully completed & verified for {workstation.machine_code}. Machine cleared for production!"
            )
        else:
            AuditLog.log(
                action=AuditLog.ActionType.PM_LOCKOUT,
                user=request.user,
                request=request,
                model_name='Workstation',
                object_id=str(workstation.id),
                object_repr=workstation.machine_code,
                new_value={'pm_status': 'FAILED', 'shift': shift, 'date': str(today)},
                details=f"Daily PM checklist FAILED for {workstation.machine_code}. One or more safety checks failed. Alert sent to Maintenance."
            )
            messages.warning(
                request,
                f"Attention: Daily PM Checklist for {workstation.machine_code} recorded FAILED checks. Machine remains LOCKED from production."
            )

        return redirect('master_data:workstation_detail', pk=workstation.pk)

    return render(request, 'master_data/pm_checklist_form.html', {
        'workstation': workstation,
        'today': today,
        'shifts': ShiftType.choices,
    })


@login_required
def tool_list(request):
    tools = InspectionTool.objects.all()
    filter_type = request.GET.get('type')
    filter_status = request.GET.get('status')

    if filter_type:
        tools = tools.filter(tool_type=filter_type)
    if filter_status:
        tools = tools.filter(status=filter_status)

    tool_types = ToolType.choices
    tool_statuses = ToolStatus.choices
    today = timezone.now().date()

    # Pre-calculate validity
    enriched_tools = []
    for tool in tools:
        enriched_tools.append({
            'tool': tool,
            'is_valid': tool.is_calibration_valid,
            'days_left': tool.days_until_expiry,
        })

    return render(request, 'master_data/tool_list.html', {
        'tools': enriched_tools,
        'tool_types': tool_types,
        'tool_statuses': tool_statuses,
        'selected_type': filter_type,
        'selected_status': filter_status,
        'today': today,
    })


@login_required
def tool_detail(request, pk):
    tool = get_object_or_404(InspectionTool, pk=pk)
    today = timezone.now().date()
    return render(request, 'master_data/tool_detail.html', {
        'tool': tool,
        'today': today,
        'is_valid': tool.is_calibration_valid,
        'days_left': tool.days_until_expiry,
    })


@login_required
@role_required(UserRole.QUALITY_ENGINEER, UserRole.QUALITY_MANAGER, UserRole.PLANT_MANAGER)
def tool_create(request):
    if request.method == 'POST':
        tool_id = request.POST.get('tool_id', '').strip()
        name = request.POST.get('name', '').strip()
        tool_type = request.POST.get('tool_type', ToolType.CALIPER)
        serial_number = request.POST.get('serial_number', '').strip()
        calibration_date_str = request.POST.get('calibration_date')
        calibration_expiry_date_str = request.POST.get('calibration_expiry_date')
        storage_location = request.POST.get('storage_location', 'Tool Crib').strip()
        notes = request.POST.get('notes', '').strip()

        try:
            calib_date = date.fromisoformat(calibration_date_str)
            expiry_date = date.fromisoformat(calibration_expiry_date_str)
            if expiry_date <= calib_date:
                messages.error(request, "Calibration expiry date must be strictly after the calibration date.")
                return render(request, 'master_data/tool_form.html', {
                    'tool_types': ToolType.choices,
                    'tool_statuses': ToolStatus.choices,
                })

            status = ToolStatus.CALIBRATED if expiry_date >= timezone.now().date() else ToolStatus.EXPIRED

            tool = InspectionTool.objects.create(
                tool_id=tool_id,
                name=name,
                tool_type=tool_type,
                serial_number=serial_number,
                calibration_date=calib_date,
                calibration_expiry_date=expiry_date,
                status=status,
                storage_location=storage_location,
                notes=notes,
            )

            AuditLog.log(
                action=AuditLog.ActionType.TOOL_REGISTERED,
                user=request.user,
                request=request,
                model_name='InspectionTool',
                object_id=str(tool.id),
                object_repr=tool.tool_id,
                new_value={'tool_id': tool.tool_id, 'expiry': str(expiry_date), 'status': status},
                details=f"Inspection tool {tool.tool_id} ({tool.name}) registered in master equipment register."
            )

            messages.success(request, f"Measuring tool '{tool.tool_id}' registered successfully.")
            return redirect('master_data:tool_list')

        except Exception as e:
            messages.error(request, f"Error registering tool: {str(e)}")

    return render(request, 'master_data/tool_form.html', {
        'tool_types': ToolType.choices,
        'tool_statuses': ToolStatus.choices,
    })


@login_required
def tool_verify_api(request):
    """
    Simulates / verifies gauge scanning for floor inspectors.
    Enforces Section 2.3: Blocks entry if gauge is expired with 'Expired Tool Calibration'.
    """
    tool_id = request.GET.get('tool_id', '').strip()
    if not tool_id:
        return JsonResponse({'success': False, 'error': 'Tool ID parameter is required.'}, status=400)

    tool = InspectionTool.objects.filter(tool_id__iexact=tool_id).first()
    if not tool:
        return JsonResponse({'success': False, 'error': f"Tool ID '{tool_id}' not found in calibration register."}, status=404)

    try:
        tool.validate_for_measurement()
        return JsonResponse({
            'success': True,
            'tool_id': tool.tool_id,
            'name': tool.name,
            'tool_type': tool.get_tool_type_display(),
            'calibration_expiry': str(tool.calibration_expiry_date),
            'status': tool.status,
            'is_valid': True,
            'message': f"Tool {tool.tool_id} is calibrated and valid for use."
        })
    except ValidationError as e:
        AuditLog.log(
            action=AuditLog.ActionType.CALIBRATION_LOCKOUT,
            user=request.user,
            request=request,
            model_name='InspectionTool',
            object_id=str(tool.id),
            object_repr=tool.tool_id,
            details=f"Tool Calibration Lockout: Attempted to use expired gauge {tool.tool_id}."
        )
        return JsonResponse({
            'success': False,
            'is_valid': False,
            'tool_id': tool.tool_id,
            'name': tool.name,
            'calibration_expiry': str(tool.calibration_expiry_date),
            'status': tool.status,
            'error': str(e.message if hasattr(e, 'message') else e),
        }, status=422)
