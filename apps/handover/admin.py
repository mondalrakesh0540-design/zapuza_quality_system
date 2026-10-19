from django.contrib import admin
from .models import ShiftHandoverLog


@admin.register(ShiftHandoverLog)
class ShiftHandoverLogAdmin(admin.ModelAdmin):
    list_display = ('log_number', 'workstation', 'outgoing_shift', 'incoming_shift', 'outgoing_operator', 'is_acknowledged', 'created_at')
    list_filter = ('is_acknowledged', 'outgoing_shift', 'incoming_shift')
    search_fields = ('log_number', 'workstation__machine_code', 'outgoing_operator__employee_id')
