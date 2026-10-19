from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.intake_list, name='intake_list'),
    path('new/', views.intake_create, name='intake_create'),
    path('<int:pk>/', views.intake_detail, name='intake_detail'),
    path('<int:pk>/mtc-verify/', views.mtc_verify, name='mtc_verify'),
    path('<int:pk>/lab-test/', views.lab_test_create, name='lab_test_create'),
    path('<int:pk>/sncr/', views.sncr_create, name='sncr_create'),
    path('quarantine/', views.sncr_list, name='sncr_list'),
    path('traceability/', views.traceability_query, name='traceability_query'),
]
