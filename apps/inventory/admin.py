from django.contrib import admin
from .models import MaterialGrade, RawMaterialIntake, MaterialLabTest, SupplierNCR


@admin.register(MaterialGrade)
class MaterialGradeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'carbon_range', 'yield_strength_min', 'requires_lab_testing', 'is_active')
    search_fields = ('code', 'name')
    list_filter = ('requires_lab_testing', 'is_active')

    def carbon_range(self, obj):
        return f"{obj.carbon_min}% - {obj.carbon_max}%"
    carbon_range.short_description = "Carbon Tol"


@admin.register(RawMaterialIntake)
class RawMaterialIntakeAdmin(admin.ModelAdmin):
    list_display = ('lot_number', 'heat_number', 'supplier_name', 'material_grade', 'quantity_received', 'unit', 'mtc_verified', 'lab_status', 'status', 'created_at')
    search_fields = ('lot_number', 'heat_number', 'supplier_name', 'purchase_order_no')
    list_filter = ('status', 'lab_status', 'mtc_verified', 'material_grade')


@admin.register(MaterialLabTest)
class MaterialLabTestAdmin(admin.ModelAdmin):
    list_display = ('intake', 'test_date', 'tested_by', 'is_passed', 'carbon_actual', 'yield_strength_actual', 'created_at')
    search_fields = ('intake__lot_number', 'intake__heat_number', 'tested_by__username')
    list_filter = ('is_passed', 'test_date')


@admin.register(SupplierNCR)
class SupplierNCRAdmin(admin.ModelAdmin):
    list_display = ('sncr_number', 'intake', 'reason_category', 'disposition', 'logged_by', 'is_resolved', 'created_at')
    search_fields = ('sncr_number', 'intake__lot_number', 'intake__heat_number')
    list_filter = ('reason_category', 'disposition', 'is_resolved')
