from functools import wraps
from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def role_required(*allowed_roles):
    """
    Decorator for views that checks whether the logged-in user has at least
    one of the specified roles (or is a superuser).
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            
            if request.user.is_superuser or request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            role_names = ", ".join(role for role in allowed_roles)
            messages.error(
                request,
                f"Access Denied: Your role '{request.user.get_role_display()}' is not authorized to access this section. "
                f"Required role(s): {role_names}."
            )
            return redirect('dashboard:index')
        return _wrapped_view
    return decorator


class RoleRequiredMixin(AccessMixin):
    """
    CBV mixin that verifies the current user has one of the allowed roles.
    """
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not request.user.is_superuser and request.user.role not in self.allowed_roles:
            messages.error(
                request,
                f"Access Denied: Your role '{request.user.get_role_display()}' does not have permission for this action."
            )
            return redirect('dashboard:index')

        return super().dispatch(request, *args, **kwargs)
