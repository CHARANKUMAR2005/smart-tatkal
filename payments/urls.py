from django.urls import path
from . import views

urlpatterns = [
    path('payment/<uuid:app_id>/', views.payment_view, name='payment'),
    path('receipt/<uuid:payment_id>/download/', views.download_receipt_view, name='download_receipt'),
]
