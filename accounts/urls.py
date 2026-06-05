from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/setup/', views.profile_setup_view, name='profile_setup'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('admin/users/', views.admin_users_view, name='admin_users'),
    path('admin/audit/', views.audit_log_view, name='audit_log'),
    path('api/colleges/search/', views.college_search_api, name='college_search_api'),
]
