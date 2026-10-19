from django.contrib import admin
from .models import WorkOrder, JobTraveler, TravelerOperation


class TravelerOperationInline(admin.TabularInline):
    model = TravelerOperation
    extra = 0
    ordering = ('operation_sequence',)


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ('work_order_number', 'part', 'raw_material_lot', 'target_quantity', 'status', 'released_by', 'created_at')
    search_fields = ('work_order_number', 'part__part_number', 'raw_material_lot__lot_number')
    list_filter = ('status', 'part')


@admin.register(JobTraveler)
class JobTravelerAdmin(admin.ModelAdmin):
    list_display = ('traveler_barcode', 'work_order', 'current_operation_sequence', 'status', 'created_at')
    search_fields = ('traveler_barcode', 'work_order__work_order_number')
    list_filter = ('status',)
    inlines = [TravelerOperationInline]


@admin.register(TravelerOperation)
class TravelerOperationAdmin(admin.ModelAdmin):
    list_display = ('traveler', 'operation_sequence', 'operation_name', 'workstation', 'status', 'completed_by', 'completed_at')
    search_fields = ('operation_name', 'traveler__traveler_barcode', 'workstation__machine_code')
    list_filter = ('status', 'requires_hold_time', 'workstation__department')
