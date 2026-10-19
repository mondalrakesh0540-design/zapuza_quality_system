from django.contrib import admin
from .models import Part, InspectionTemplate, InspectionTemplateRevision, Blueprint, InspectionParameter, BlueprintPin


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ('part_number', 'part_name', 'material_grade', 'drawing_number', 'revision_level', 'is_active')
    search_fields = ('part_number', 'part_name', 'drawing_number')
    list_filter = ('material_grade', 'is_active')


@admin.register(InspectionTemplate)
class InspectionTemplateAdmin(admin.ModelAdmin):
    list_display = ('template_code', 'title', 'part', 'template_type', 'created_at')
    search_fields = ('template_code', 'title', 'part__part_number')
    list_filter = ('template_type',)


@admin.register(InspectionTemplateRevision)
class InspectionTemplateRevisionAdmin(admin.ModelAdmin):
    list_display = ('template', 'revision_label', 'status', 'created_by', 'approved_by', 'approved_at')
    search_fields = ('template__template_code', 'revision_label', 'created_by__username')
    list_filter = ('status',)


@admin.register(Blueprint)
class BlueprintAdmin(admin.ModelAdmin):
    list_display = ('title', 'template_revision', 'uploaded_at')
    search_fields = ('title', 'template_revision__template__template_code')


@admin.register(InspectionParameter)
class InspectionParameterAdmin(admin.ModelAdmin):
    list_display = ('sequence_order', 'parameter_name', 'template_revision', 'parameter_type', 'is_ctq', 'required_tool_type')
    search_fields = ('parameter_name', 'template_revision__template__template_code')
    list_filter = ('parameter_type', 'is_ctq', 'required_tool_type')


@admin.register(BlueprintPin)
class BlueprintPinAdmin(admin.ModelAdmin):
    list_display = ('pin_number', 'label', 'blueprint', 'coordinate_x', 'coordinate_y', 'parameter')
    search_fields = ('label', 'blueprint__title')
