from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'employee_id', 'role', 'first_name', 'last_name', 'is_shift_active', 'is_staff')
    list_filter = ('role', 'is_shift_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'employee_id', 'first_name', 'last_name', 'email')
    ordering = ('employee_id',)

    fieldsets = UserAdmin.fieldsets + (
        ('Factory Quality Roles & Details', {
            'fields': ('employee_id', 'role', 'phone_number', 'shift_preference', 'is_shift_active'),
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Factory Quality Roles & Details', {
            'fields': ('employee_id', 'role', 'phone_number', 'shift_preference', 'is_shift_active'),
        }),
    )
