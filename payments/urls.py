from django.urls import path
from . import views

urlpatterns = [
    path('payment/<uuid:app_id>/', views.payment_view, name='payment'),
    path('payment/callback/', views.razorpay_callback, name='razorpay_callback'),
    path('receipt/<uuid:payment_id>/download/', views.download_receipt_view, name='download_receipt'),
]
