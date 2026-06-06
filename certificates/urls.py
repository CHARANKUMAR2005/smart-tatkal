from django.urls import path
from . import views

urlpatterns = [
    path('apply/', views.apply_view, name='apply'),
    path('applications/', views.my_applications_view, name='my_applications'),
    path('applications/<uuid:app_id>/', views.application_detail_view, name='application_detail'),
    path('staff/applications/', views.staff_applications_view, name='staff_applications'),
    path('staff/applications/<uuid:app_id>/status/', views.update_status_view, name='update_status'),
    path('certificates/<uuid:cert_id>/download/', views.download_certificate_view, name='download_certificate'),
    path('verify/<str:code>/', views.verify_certificate_view, name='verify_certificate'),
    path('ajax/fee/', views.get_fee_ajax, name='get_fee_ajax'),
    path('api/colleges/search/', views.college_search_api, name='college_search_api'),
    path('admin/test-email/', views.test_email_view, name='test_email'),
    # New routes
    path('track/', views.track_certificate_view, name='track_certificate'),
    path('admin/analytics/', views.analytics_view, name='analytics'),
    path('admin/availability/', views.admin_availability_view, name='admin_availability'),
    path('admin/reports/', views.reports_view, name='reports'),
]
