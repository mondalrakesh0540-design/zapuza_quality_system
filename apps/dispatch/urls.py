from django.urls import path
from . import views

app_name = 'dispatch'

urlpatterns = [
    path('', views.dispatch_queue_view, name='dispatch_queue'),
    path('clear/<int:traveler_id>/', views.dispatch_create_view, name='dispatch_create'),
    path('gate-pass/<int:manifest_id>/', views.dispatch_gate_pass_view, name='dispatch_gate_pass'),
    path('crate-label/<int:manifest_id>/', views.dispatch_crate_label_view, name='dispatch_crate_label'),
    path('verify/<str:token>/', views.customer_shipping_verify_view, name='customer_verify'),
]
