from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from apps.audit_trail.models import AuditLog
from .models import User, UserRole


def login_view(request):
    # Check if demo quick-login was clicked (works even if already logged in)
    if request.method == 'POST' and request.POST.get('demo_role'):
        demo_role = request.POST.get('demo_role')
        user = User.objects.filter(role=demo_role).first()
        if user:
            login(request, user)
            AuditLog.log(
                action=AuditLog.ActionType.LOGIN,
                user=user,
                request=request,
                details=f"Demo quick-login as {user.get_role_display()} ({user.employee_id})"
            )
            messages.success(request, f"Active role: {user.get_full_name() or user.username} ({user.get_role_display()})")
            return redirect('dashboard:index')
        else:
            messages.error(request, f"No demo user found for role '{demo_role}'. Run the seed command first.")
            return redirect('accounts:login')

    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if not user.is_active or not user.is_shift_active:
                messages.error(request, "Account is disabled or inactive for this shift.")
                return render(request, 'accounts/login.html')

            login(request, user)
            AuditLog.log(
                action=AuditLog.ActionType.LOGIN,
                user=user,
                request=request,
                details=f"Successful credential login as {user.get_role_display()} ({user.employee_id})"
            )
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            next_url = request.GET.get('next')
            return redirect(next_url if next_url else 'dashboard:index')
        else:
            AuditLog.log(
                action=AuditLog.ActionType.SECURITY_ALERT,
                request=request,
                details=f"Failed login attempt for username '{username}'"
            )
            messages.error(request, "Invalid username or password. Please verify your credentials.")

    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    user = request.user
    AuditLog.log(
        action=AuditLog.ActionType.LOGOUT,
        user=user,
        request=request,
        details=f"User {user.username} logged out"
    )
    logout(request)
    messages.info(request, "You have been logged out securely.")
    return redirect('accounts:login')


@login_required
def profile_view(request):
    user_recent_audits = AuditLog.objects.filter(user=request.user)[:10]
    return render(request, 'accounts/profile.html', {
        'recent_audits': user_recent_audits,
    })
