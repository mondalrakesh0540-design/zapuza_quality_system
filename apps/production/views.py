from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from apps.accounts.models import UserRole
from apps.accounts.permissions import role_required
from apps.audit_trail.models import AuditLog
from apps.inventory.models import IntakeStatus, RawMaterialIntake
from apps.master_data.models import Workstation
from apps.quality.models import InspectionTemplate, Part, RevisionStatus
from .models import (
    JobTraveler,
    JobTravelerStatus,
    OperationStatus,
    TravelerOperation,
    WorkOrder,
    WorkOrderStatus,
)


@login_required
def work_order_list(request):
    status_filter = request.GET.get('status')
    orders = WorkOrder.objects.select_related('part', 'raw_material_lot', 'released_by').all()

    if status_filter:
        orders = orders.filter(status=status_filter)

    return render(request, 'production/work_order_list.html', {
        'orders': orders,
        'statuses': WorkOrderStatus.choices,
        'selected_status': status_filter,
    })


@login_required
@role_required(UserRole.SHIFT_SUPERVISOR, UserRole.PLANT_MANAGER, UserRole.QUALITY_MANAGER)
def work_order_create(request):
    if request.method == 'POST':
        work_order_number = request.POST.get('work_order_number', '').strip().upper()
        part_id = request.POST.get('part')
        lot_id = request.POST.get('raw_material_lot')
        target_qty_str = request.POST.get('target_quantity', '').strip()

        if not work_order_number:
            count = WorkOrder.objects.count() + 1
            work_order_number = f"WO-{timezone.now().year}-{count:03d}"

        try:
            part = get_object_or_404(Part, pk=part_id)
            lot = get_object_or_404(RawMaterialIntake, pk=lot_id)
            target_quantity = int(target_qty_str)

            # Check raw material issuance authorization
            lot.validate_for_work_order_issue()

            order = WorkOrder.objects.create(
                work_order_number=work_order_number,
                part=part,
                raw_material_lot=lot,
                target_quantity=target_quantity,
                status=WorkOrderStatus.DRAFT,
            )

            messages.success(request, f"Work Order '{order.work_order_number}' created in Draft. Ready for shopfloor release.")
            return redirect('production:work_order_list')

        except Exception as e:
            messages.error(request, f"Error creating work order: {str(e)}")

    # Filter available raw stock lots (only those cleared for production)
    eligible_lots = [
        lot for lot in RawMaterialIntake.objects.filter(status=IntakeStatus.IN_STORE, mtc_verified=True)
        if lot.can_issue_to_production()[0]
    ]

    return render(request, 'production/work_order_form.html', {
        'parts': Part.objects.filter(is_active=True),
        'lots': eligible_lots,
    })


@login_required
@role_required(UserRole.SHIFT_SUPERVISOR, UserRole.PLANT_MANAGER)
def work_order_release(request, pk):
    """
    Release work order and generate digital Job Traveler with sequential operations.
    """
    order = get_object_or_404(WorkOrder, pk=pk)

    if request.method == 'POST':
        try:
            traveler = order.release(request.user)

            # Auto-populate master sequential routing operations if traveler has no operations
            if not traveler.operations.exists():
                workstations = list(Workstation.objects.filter(is_active=True))
                ws_sawing = next((w for w in workstations if 'MACH' in w.department.code), workstations[0] if workstations else None)
                ws_turning = next((w for w in workstations if 'CNC' in w.machine_code), ws_sawing)
                ws_heat = next((w for w in workstations if 'HEAT' in w.department.code or 'OVEN' in w.machine_code), ws_turning)
                ws_grinding = next((w for w in workstations if 'GRIND' in w.machine_code or 'VMC' in w.machine_code), ws_turning)
                ws_assy = next((w for w in workstations if 'ASSY' in w.department.code or 'LINE' in w.machine_code), ws_turning)

                # Fetch active template revisions if any
                pdi_rev = None
                pdi_template = InspectionTemplate.objects.filter(part=order.part).first()
                if pdi_template:
                    pdi_rev = pdi_template.get_approved_revision() or pdi_template.get_latest_revision()

                ops_data = [
                    (10, 'Op 10: Raw Material Cutting & Billet Prep', ws_sawing, False, 0, None, OperationStatus.READY),
                    (20, 'Op 20: CNC Rough Turning & Profiling', ws_turning, False, 0, None, OperationStatus.PENDING),
                    (30, 'Op 30: Vacuum Heat Treatment Discharge', ws_heat, True, 240, None, OperationStatus.PENDING),  # 4-hr cooling hold
                    (40, 'Op 40: Precision Cylindrical Grinding', ws_grinding, False, 0, None, OperationStatus.PENDING),
                    (50, 'Op 50: Final Pre-Dispatch Inspection (PDI) & Wash', ws_assy, False, 0, pdi_rev, OperationStatus.PENDING),
                ]

                for seq, name, ws, hold, hold_min, rev, initial_status in ops_data:
                    TravelerOperation.objects.create(
                        traveler=traveler,
                        operation_sequence=seq,
                        operation_name=name,
                        workstation=ws,
                        requires_hold_time=hold,
                        hold_duration_minutes=hold_min,
                        inspection_template_revision=rev,
                        status=initial_status,
                    )

            AuditLog.log(
                action=AuditLog.ActionType.WORK_ORDER_RELEASED,
                user=request.user,
                request=request,
                model_name='WorkOrder',
                object_id=str(order.id),
                object_repr=order.work_order_number,
                details=f"Work Order {order.work_order_number} released to shopfloor. Job Traveler {traveler.traveler_barcode} generated with sequential operations."
            )

            messages.success(request, f"Work Order {order.work_order_number} released. Job Traveler '{traveler.traveler_barcode}' active on shopfloor.")
            return redirect('production:traveler_detail', pk=traveler.pk)

        except ValidationError as e:
            messages.error(request, f"Release Blocked: {str(e.message if hasattr(e, 'message') else e)}")

    return redirect('production:work_order_list')


@login_required
def traveler_detail(request, pk):
    """
    Digital Job Traveler view (BRD Section 7.1).
    Displays sequential routing progression, interlocks, and machine PM status.
    """
    traveler = get_object_or_404(
        JobTraveler.objects.select_related('work_order', 'work_order__part', 'work_order__raw_material_lot'),
        pk=pk
    )
    operations = traveler.operations.select_related('workstation', 'workstation__department', 'completed_by', 'inspection_template_revision').all()

    # Precompute sequential start clearance for each operation
    enriched_ops = []
    for op in operations:
        can_start, start_reason = op.can_start()
        hold_active, remaining_min = op.is_hold_active()
        enriched_ops.append({
            'op': op,
            'can_start': can_start,
            'start_reason': start_reason,
            'hold_active': hold_active,
            'remaining_min': remaining_min,
        })

    return render(request, 'production/traveler_detail.html', {
        'traveler': traveler,
        'operations': enriched_ops,
    })


@login_required
@role_required(UserRole.SHIFT_SUPERVISOR, UserRole.QA_FLOOR_INSPECTOR, UserRole.PLANT_MANAGER)
def operation_action(request, op_id):
    """
    Executes operation start or sign-off with strict server-side sequential interlock.
    """
    operation = get_object_or_404(TravelerOperation, pk=op_id)
    action = request.POST.get('action')

    if action == 'start':
        can_run, reason = operation.can_start()
        if not can_run:
            AuditLog.log(
                action=AuditLog.ActionType.ROUTING_LOCKOUT,
                user=request.user,
                request=request,
                model_name='TravelerOperation',
                object_id=str(operation.id),
                object_repr=f"Op {operation.operation_sequence}",
                details=f"Routing start blocked on {operation.operation_name}: {reason}"
            )
            messages.error(request, f"Interlock Blocked: {reason}")
            return redirect('production:traveler_detail', pk=operation.traveler.pk)

        operation.start_operation(request.user)
        messages.success(request, f"Operation '{operation.operation_name}' started on {operation.workstation.machine_code}.")

    elif action == 'complete':
        remarks = request.POST.get('remarks', '').strip()
        operation.complete_operation(request.user, remarks=remarks)

        AuditLog.log(
            action=AuditLog.ActionType.ROUTING_COMPLETED,
            user=request.user,
            request=request,
            model_name='TravelerOperation',
            object_id=str(operation.id),
            object_repr=f"Op {operation.operation_sequence}",
            details=f"Op {operation.operation_sequence} ({operation.operation_name}) completed and electronically signed off by {request.user.employee_id}."
        )

        messages.success(request, f"Op {operation.operation_sequence} completed! Downstream operation in process sequence is now unlocked.")

    return redirect('production:traveler_detail', pk=operation.traveler.pk)
