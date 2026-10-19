from django.urls import path
from . import views

app_name = 'production'

urlpatterns = [
    path('work-orders/', views.work_order_list, name='work_order_list'),
    path('work-orders/new/', views.work_order_create, name='work_order_create'),
    path('work-orders/<int:pk>/release/', views.work_order_release, name='work_order_release'),
    path('travelers/<int:pk>/', views.traveler_detail, name='traveler_detail'),
    path('operations/<int:op_id>/action/', views.operation_action, name='operation_action'),
]
