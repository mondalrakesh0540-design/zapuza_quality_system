from django.urls import path
from . import views

app_name = 'quality'

urlpatterns = [
    path('templates/', views.template_list, name='template_list'),
    path('templates/new/', views.template_create, name='template_create'),
    path('templates/<int:pk>/', views.template_detail, name='template_detail'),
    path('revisions/<int:revision_id>/parameters/add/', views.parameter_create, name='parameter_create'),
    path('revisions/<int:revision_id>/blueprints/upload/', views.blueprint_upload, name='blueprint_upload'),
    path('revisions/<int:revision_id>/approve/', views.template_revision_approve, name='template_revision_approve'),
    path('blueprints/<int:blueprint_id>/pins/api/', views.blueprint_pin_api, name='blueprint_pin_api'),

    # Phase 4: Floor Inspector Tablet, Dual QR Scanner, and Supervisor Reviews
    path('floor/scan/', views.floor_scan_view, name='floor_scan'),
    path('floor/scan/validate/', views.floor_scan_validate, name='floor_scan_validate'),
    path('floor/inspect/<int:op_id>/', views.floor_inspect_view, name='floor_inspect'),
    path('supervisor/queue/', views.supervisor_queue_view, name='supervisor_queue'),
    path('supervisor/review/<int:inspection_id>/', views.supervisor_review_view, name='supervisor_review'),

    # Phase 5A: Final Pre-Dispatch Inspection (PDI)
    path('pdi/', views.pdi_queue_view, name='pdi_queue'),
    path('pdi/<int:traveler_id>/inspect/', views.pdi_execute_view, name='pdi_execute'),

    # Phase 5B: Certificate of Conformance (CoC)
    path('coc/list/', views.coc_list_view, name='coc_list'),
    path('coc/generate/<int:traveler_id>/', views.coc_generate_view, name='coc_generate'),
    path('coc/<int:coc_id>/', views.coc_detail_view, name='coc_detail'),
    path('coc/<int:coc_id>/download/', views.coc_download_view, name='coc_download'),
    path('coc/verify/<str:token>/', views.coc_verify_view, name='coc_verify'),

    # Phase 5D: Material Review Board (MRB) Digital Disposition (BRD Section 6.3)
    path('mrb/', views.mrb_queue_view, name='mrb_queue'),
    path('mrb/traveler/<int:traveler_id>/', views.mrb_disposition_traveler_view, name='mrb_disposition_traveler'),
    path('mrb/lot/<int:lot_id>/', views.mrb_disposition_lot_view, name='mrb_disposition_lot'),
    path('mrb/<int:disposition_id>/', views.mrb_detail_view, name='mrb_detail'),
]
