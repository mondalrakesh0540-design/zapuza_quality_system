from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from apps.accounts.models import UserRole
from apps.accounts.permissions import role_required
from .models import AuditLog


@login_required
@role_required(UserRole.PLANT_MANAGER, UserRole.QUALITY_MANAGER)
def audit_log_list(request):
    logs = AuditLog.objects.select_related('user').all()
    action_filter = request.GET.get('action')
    role_filter = request.GET.get('role')

    if action_filter:
        logs = logs.filter(action=action_filter)
    if role_filter:
        logs = logs.filter(user_role=role_filter)

    logs = logs[:100]  # Paginated/limited to latest 100 entries

    return render(request, 'audit_trail/audit_log_list.html', {
        'logs': logs,
        'action_choices': AuditLog.ActionType.choices,
        'selected_action': action_filter,
        'selected_role': role_filter,
    })
