from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dashboard_view, name='index'),
    path('dashboard/', views.dashboard_view, name='dashboard_direct'),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('master-data/', include('apps.master_data.urls', namespace='master_data')),
    path('audit-trail/', include('apps.audit_trail.urls', namespace='audit_trail')),
    path('inventory/', include('apps.inventory.urls', namespace='inventory')),
    path('quality/', include('apps.quality.urls', namespace='quality')),
    path('production/', include('apps.production.urls', namespace='production')),
    path('dispatch/', include('apps.dispatch.urls', namespace='dispatch')),
    path('handover/', include('apps.handover.urls', namespace='handover')),
]

# Provide dashboard namespace
dashboard_patterns = ([
    path('', views.dashboard_view, name='index'),
], 'dashboard')

urlpatterns += [
    path('app/dashboard/', include(dashboard_patterns, namespace='dashboard')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
