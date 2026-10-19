from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user_identifier', 'user_role', 'action', 'model_name', 'object_repr', 'ip_address')
    list_filter = ('action', 'user_role', 'timestamp')
    search_fields = ('user_identifier', 'action', 'model_name', 'object_repr', 'details', 'ip_address')
    readonly_fields = [f.name for f in AuditLog._meta.fields]
    ordering = ('-timestamp',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
