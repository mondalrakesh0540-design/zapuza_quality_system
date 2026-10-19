from django.contrib import admin
from .models import Department, Workstation, MachinePMLog, InspectionTool


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active', 'created_at')
    search_fields = ('code', 'name')
    list_filter = ('is_active',)


@admin.register(Workstation)
class WorkstationAdmin(admin.ModelAdmin):
    list_display = ('machine_code', 'name', 'department', 'status', 'is_active', 'daily_pm_status')
    search_fields = ('machine_code', 'name', 'qr_code_identifier')
    list_filter = ('department', 'status', 'is_active')

    def daily_pm_status(self, obj):
        return "PASSED" if obj.is_daily_pm_completed() else "OVERDUE / FAILED"
    daily_pm_status.short_description = "Today's PM"


@admin.register(MachinePMLog)
class MachinePMLogAdmin(admin.ModelAdmin):
    list_display = ('workstation', 'log_date', 'shift', 'completed_by', 'is_passed', 'created_at')
    list_filter = ('is_passed', 'shift', 'log_date', 'workstation__department')
    search_fields = ('workstation__machine_code', 'completed_by__username', 'remarks')


@admin.register(InspectionTool)
class InspectionToolAdmin(admin.ModelAdmin):
    list_display = ('tool_id', 'name', 'tool_type', 'serial_number', 'calibration_expiry_date', 'status', 'is_valid')
    list_filter = ('tool_type', 'status', 'calibration_expiry_date')
    search_fields = ('tool_id', 'name', 'serial_number')

    def is_valid(self, obj):
        return obj.is_calibration_valid
    is_valid.boolean = True
    is_valid.short_description = "Valid for Use"
