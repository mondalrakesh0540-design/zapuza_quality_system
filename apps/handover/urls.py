from django.urls import path
from . import views

app_name = 'handover'

urlpatterns = [
    path('', views.handover_list_view, name='handover_list'),
    path('new/', views.handover_create_view, name='handover_create'),
    path('<int:log_id>/', views.handover_detail_view, name='handover_detail'),
    path('<int:log_id>/acknowledge/', views.handover_acknowledge_view, name='handover_acknowledge'),
]
