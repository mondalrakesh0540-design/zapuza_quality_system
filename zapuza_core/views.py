from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import render
from django.utils import timezone
from apps.audit_trail.models import AuditLog
from apps.dispatch.models import DispatchManifest
from apps.handover.models import ShiftHandoverLog, ShiftHandoverStatus
from apps.master_data.models import (
    Department,
    InspectionTool,
    MachinePMLog,
    ToolStatus,
    Workstation,
    WorkstationStatus,
)
from apps.production.models import (
    JobTraveler,
    JobTravelerStatus,
    OperationStatus,
    TravelerOperation,
    WorkOrder,
)
from apps.quality.models import (
    FloorInspection,
    FloorInspectionStatus,
    MRBDisposition,
)


@login_required
def dashboard_view(request):
    """
    Factory Operations & Quality Control Center - Live Shopfloor & Executive Analytics Dashboard.
    Conforms to BRD Section 1.2 & Section 8.3:
    - Real-Time Workstation Status, PM Clearance, and Calibration Interlocks
    - Shopfloor Bottleneck Detection & WIP Queue Tracking
    - First-Pass Yield (FPY %) & Scrap Rate Analytics
    - Shift Handover Compliance & Dispatch Gate Stats
    """
    today = timezone.now().date()
    workstations = Workstation.objects.select_related('department').all()

    total_workstations = workstations.count()
    cleared_count = 0
    locked_count = 0
    active_bottlenecks = 0
    workstation_statuses = []

    for ws in workstations:
        can_start, reason = ws.can_start_job(date=today)
        if can_start:
            cleared_count += 1
        else:
            locked_count += 1

        # Count active WIP operations assigned to this workstation
        queue_count = TravelerOperation.objects.filter(
            workstation=ws,
            status__in=[OperationStatus.PENDING, OperationStatus.READY, OperationStatus.RUNNING]
        ).count()
        is_bottleneck = queue_count >= 3
        if is_bottleneck:
            active_bottlenecks += 1

        workstation_statuses.append({
            'ws': ws,
            'can_start': can_start,
            'reason': reason if not can_start else "Ready for production",
            'queue_count': queue_count,
            'is_bottleneck': is_bottleneck,
        })

    # Sort so workstations with largest backlog queues appear first
    workstation_statuses.sort(key=lambda x: (not x['is_bottleneck'], -x['queue_count']))

    # Tool Calibration Metrics
    tools = InspectionTool.objects.all()
    total_tools = tools.count()
    valid_tools = tools.filter(status=ToolStatus.CALIBRATED, calibration_expiry_date__gte=today).count()
    expired_tools = total_tools - valid_tools

    # Production & Quality Metrics (BRD Section 8.3)
    completed_inspections = FloorInspection.objects.filter(
        status__in=[
            FloorInspectionStatus.APPROVED,
            FloorInspectionStatus.CONCESSION_APPROVED,
            FloorInspectionStatus.REJECTED_QUARANTINED
        ]
    )
    total_completed_insp = completed_inspections.count()
    first_pass_passed = completed_inspections.filter(
        status=FloorInspectionStatus.APPROVED,
        overall_in_tolerance=True
    ).count()

    if total_completed_insp > 0:
        fpy_rate = round((first_pass_passed / total_completed_insp) * 100, 1)
    else:
        fpy_rate = 100.0

    wo_aggregates = WorkOrder.objects.aggregate(
        completed=models.Sum('completed_quantity'),
        scrapped=models.Sum('scrapped_quantity')
    )
    total_completed_units = wo_aggregates['completed'] or 0
    total_scrapped_units = wo_aggregates['scrapped'] or 0
    total_units_manufactured = total_completed_units + total_scrapped_units

    if total_units_manufactured > 0:
        scrap_rate = round((total_scrapped_units / total_units_manufactured) * 100, 1)
    else:
        scrap_rate = 0.0

    # Active WIP & Quarantine Counts
    active_travelers_count = JobTraveler.objects.filter(status=JobTravelerStatus.ACTIVE).count()
    quarantined_travelers_count = JobTraveler.objects.filter(status=JobTravelerStatus.QUARANTINED).count()
    mrb_dispositions_count = MRBDisposition.objects.count()
    pending_handovers_count = ShiftHandoverLog.objects.filter(status=ShiftHandoverStatus.PENDING_ACK).count()
    dispatches_count = DispatchManifest.objects.count()

    recent_pm_logs = MachinePMLog.objects.select_related('workstation', 'completed_by').order_by('-created_at')[:6]
    recent_audits = AuditLog.objects.order_by('-timestamp')[:8]

    pm_completion_rate = int((cleared_count / total_workstations * 100)) if total_workstations > 0 else 0

    return render(request, 'dashboard/index.html', {
        'today': today,
        'total_workstations': total_workstations,
        'cleared_workstations': cleared_count,
        'locked_workstations': locked_count,
        'pm_completion_rate': pm_completion_rate,
        'total_tools': total_tools,
        'valid_tools': valid_tools,
        'expired_tools': expired_tools,
        'fpy_rate': fpy_rate,
        'first_pass_passed': first_pass_passed,
        'total_completed_insp': total_completed_insp,
        'total_scrapped_units': total_scrapped_units,
        'total_completed_units': total_completed_units,
        'scrap_rate': scrap_rate,
        'active_travelers_count': active_travelers_count,
        'quarantined_travelers_count': quarantined_travelers_count,
        'mrb_dispositions_count': mrb_dispositions_count,
        'pending_handovers_count': pending_handovers_count,
        'dispatches_count': dispatches_count,
        'active_bottlenecks': active_bottlenecks,
        'workstation_statuses': workstation_statuses,
        'recent_pm_logs': recent_pm_logs,
        'recent_audits': recent_audits,
    })
