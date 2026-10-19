from django.urls import path
from . import views

app_name = 'master_data'

urlpatterns = [
    path('workstations/', views.workstation_list, name='workstation_list'),
    path('workstations/<int:pk>/', views.workstation_detail, name='workstation_detail'),
    path('workstations/<int:pk>/pm/', views.workstation_pm_create, name='workstation_pm_create'),
    path('tools/', views.tool_list, name='tool_list'),
    path('tools/create/', views.tool_create, name='tool_create'),
    path('tools/<int:pk>/', views.tool_detail, name='tool_detail'),
    path('api/tools/verify/', views.tool_verify_api, name='tool_verify_api'),
]
