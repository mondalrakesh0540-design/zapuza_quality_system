from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from apps.accounts.models import UserRole
from apps.audit_trail.models import AuditLog
from apps.master_data.models import Workstation, ShiftType
from apps.production.models import JobTraveler
from .models import ShiftHandoverLog, ShiftHandoverStatus


@login_required
def handover_list_view(request):
    """
    List and filter all digital shift handover logs.
    Conforms to BRD Section 12.2.
    """
    ws_filter = request.GET.get('workstation')
    status_filter = request.GET.get('status')

    logs = ShiftHandoverLog.objects.select_related(
        'workstation', 'outgoing_operator', 'incoming_operator', 'active_traveler'
    ).all()

    if ws_filter:
        logs = logs.filter(workstation_id=ws_filter)

    if status_filter:
        logs = logs.filter(status=status_filter)

    workstations = Workstation.objects.filter(is_active=True)

    return render(request, 'handover/handover_list.html', {
        'logs': logs,
        'workstations': workstations,
        'selected_ws': ws_filter,
        'selected_status': status_filter,
    })


@login_required
def handover_create_view(request):
    """
    Outgoing operator logs shift handover on station tablet.
    Records: open job status, parts produced, scrap segregated, tool wear, machine health, quality alerts.
    """
    if not request.user.can_log_handover:
        messages.error(request, "Permission Denied: Only shopfloor operators and supervisors can submit shift handovers.")
        return redirect('handover:handover_list')

    workstations = Workstation.objects.filter(is_active=True)
    active_travelers = JobTraveler.objects.filter(status='ACTIVE').select_related('work_order', 'work_order__part')

    if request.method == 'POST':
        ws_id = request.POST.get('workstation')
        out_shift = request.POST.get('outgoing_shift')
        in_shift = request.POST.get('incoming_shift')
        traveler_id = request.POST.get('active_traveler')
        parts_count = int(request.POST.get('parts_produced_count', 0) or 0)
        scrap_count = int(request.POST.get('scrap_count', 0) or 0)
        tool_wear = request.POST.get('tool_wear_status', '').strip()
        machine_health = request.POST.get('machine_health_notes', '').strip()
        quality_alerts = request.POST.get('open_quality_alerts', '').strip()
        pending_pdi = request.POST.get('pending_pdi_reviews', '').strip()

        if not (ws_id and out_shift and in_shift and tool_wear and machine_health):
            messages.error(request, "Validation Error: Workstation, Shifts, Tool Wear, and Machine Health are mandatory.")
            return render(request, 'handover/handover_form.html', {
                'workstations': workstations,
                'active_travelers': active_travelers,
                'shift_choices': ShiftType.choices,
            })

        workstation = get_object_or_404(Workstation, pk=ws_id)
        traveler = JobTraveler.objects.filter(pk=traveler_id).first() if traveler_id else None

        with transaction.atomic():
            log_num = f"SHL-{workstation.machine_code}-{int(timezone.now().timestamp())}"

            log = ShiftHandoverLog.objects.create(
                log_number=log_num,
                workstation=workstation,
                outgoing_shift=out_shift,
                incoming_shift=in_shift,
                outgoing_operator=request.user,
                active_traveler=traveler,
                parts_produced_count=parts_count,
                scrap_count=scrap_count,
                tool_wear_status=tool_wear,
                machine_health_notes=machine_health,
                open_quality_alerts=quality_alerts,
                pending_pdi_reviews=pending_pdi,
                status=ShiftHandoverStatus.PENDING_ACK,
            )

            AuditLog.log(
                action=AuditLog.ActionType.SHIFT_HANDOVER,
                user=request.user,
                request=request,
                model_name='ShiftHandoverLog',
                object_id=str(log.id),
                object_repr=log.log_number,
                details=f"Shift Handover {log.log_number} logged for workstation {workstation.machine_code} ({out_shift} -> {in_shift})."
            )

            messages.success(request, f"Shift Handover {log.log_number} successfully recorded! Pending incoming operator sign-off.")
            return redirect('handover:handover_detail', log_id=log.id)

    return render(request, 'handover/handover_form.html', {
        'workstations': workstations,
        'active_travelers': active_travelers,
        'shift_choices': ShiftType.choices,
    })


@login_required
def handover_detail_view(request, log_id):
    """
    Detailed view of a shift handover log with incoming acknowledgment actions.
    """
    log = get_object_or_404(
        ShiftHandoverLog.objects.select_related(
            'workstation', 'outgoing_operator', 'incoming_operator', 'active_traveler', 'active_traveler__work_order'
        ),
        pk=log_id
    )

    return render(request, 'handover/handover_detail.html', {
        'log': log,
    })


@login_required
def handover_acknowledge_view(request, log_id):
    """
    Incoming operator digitally reviews and acknowledges the shift handover log.
    Enforces that workers cannot operate machine without acknowledging open health notes.
    """
    log = get_object_or_404(ShiftHandoverLog, pk=log_id)

    if log.is_acknowledged:
        messages.info(request, "This shift handover log has already been acknowledged.")
        return redirect('handover:handover_detail', log_id=log.id)

    if request.method == 'POST':
        remarks = request.POST.get('incoming_notes', '').strip()
        log.acknowledge(incoming_user=request.user, remarks=remarks)

        AuditLog.log(
            action=AuditLog.ActionType.SHIFT_HANDOVER_ACK,
            user=request.user,
            request=request,
            model_name='ShiftHandoverLog',
            object_id=str(log.id),
            object_repr=log.log_number,
            details=f"Shift Handover {log.log_number} acknowledged by {request.user.employee_id} ({request.user.role})."
        )

        messages.success(request, f"Shift Handover {log.log_number} formally acknowledged. Workstation is cleared for production.")
        return redirect('handover:handover_detail', log_id=log.id)

    return redirect('handover:handover_detail', log_id=log.id)
