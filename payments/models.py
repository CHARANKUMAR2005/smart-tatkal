from django.db import models
from certificates.models import Application
import uuid

class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('razorpay', 'Razorpay'), ('upi', 'UPI'), ('debit_card', 'Debit Card'),
        ('credit_card', 'Credit Card'), ('net_banking', 'Net Banking'), ('demo', 'Demo Payment'),
    ]
    STATUS_CHOICES = [('pending','Pending'), ('success','Success'), ('failed','Failed'), ('refunded','Refunded')]

    payment_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, blank=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='demo')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    gateway_response = models.JSONField(default=dict, blank=True)
    payment_screenshot = models.ImageField(upload_to='payment_screenshots/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment ₹{self.amount} - {self.status}"
