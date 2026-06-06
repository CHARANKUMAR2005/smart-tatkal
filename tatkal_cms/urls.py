from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('', include('certificates.urls')),
    path('', include('payments.urls')),
    path('', include('notifications.urls')),
    # Serve media files in all environments (Django's static() helper is a no-op
    # when DEBUG=False, which causes 404 for uploaded files in production).
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
