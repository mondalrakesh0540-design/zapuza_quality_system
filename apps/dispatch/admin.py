from django.contrib import admin
from .models import DispatchManifest


@admin.register(DispatchManifest)
class DispatchManifestAdmin(admin.ModelAdmin):
    list_display = ('manifest_number', 'customer_name', 'customer_po_number', 'traveler', 'status', 'cleared_at')
    list_filter = ('status', 'cleared_at')
    search_fields = ('manifest_number', 'customer_name', 'customer_po_number', 'traveler__traveler_barcode')
