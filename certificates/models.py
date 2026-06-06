from django.db import models
from django.conf import settings
from accounts.models import User, StudentProfile, Institution, College
import uuid

CERTIFICATE_TYPES = [
    ('bonafide', 'Bonafide Certificate'),
    ('study', 'Study Certificate'),
    ('transfer', 'Transfer Certificate'),
    ('course_completion', 'Course Completion Certificate'),
    ('medium', 'Medium of Instruction Certificate'),
    ('provisional', 'Provisional Certificate'),
    ('migration', 'Migration Certificate'),
    ('income', 'Income Certificate'),
    ('internship', 'Internship Certificate'),
    ('character', 'Character Certificate'),
]

STATUS_CHOICES = [
    ('submitted', 'Submitted'),
    ('under_verification', 'Under Verification'),
    ('document_issue', 'Document Issue'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('generated', 'Certificate Generated'),
    ('delivered', 'Delivered'),
]

class Application(models.Model):
    application_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='applications')
    institution = models.ForeignKey(Institution, on_delete=models.SET_NULL, null=True, blank=True)
    college = models.ForeignKey(College, on_delete=models.SET_NULL, null=True, blank=True, related_name='applications')
    certificate_type = models.CharField(max_length=30, choices=CERTIFICATE_TYPES)
    purpose = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    is_tatkal = models.BooleanField(default=False)
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=[('pending','Pending'),('paid','Paid'),('failed','Failed')], default='pending')
    remarks = models.TextField(blank=True)
    staff_remarks = models.TextField(blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_applications')
    document1 = models.FileField(upload_to='application_docs/', blank=True, null=True)
    document2 = models.FileField(upload_to='application_docs/', blank=True, null=True)
    document3 = models.FileField(upload_to='application_docs/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_certificate_type_display()} - {self.student.user.get_full_name()}"

    def get_short_id(self):
        return str(self.application_id)[:8].upper()

class Certificate(models.Model):
    certificate_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='certificate')
    verification_code = models.CharField(max_length=20, unique=True)
    pdf_path = models.FileField(upload_to='certificates/', blank=True, null=True)
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True, null=True)
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    is_valid = models.BooleanField(default=True)
    download_count = models.IntegerField(default=0)

    def __str__(self):
        return f"Certificate #{self.verification_code}"

class ApplicationStatusHistory(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    note = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.application.get_short_id()} → {self.to_status}"


class DeliveryDetails(models.Model):
    DELIVERY_CHOICES = [
        ('collect', 'Collect from College'),
        ('home', 'Home Delivery'),
    ]
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='delivery')
    method = models.CharField(max_length=10, choices=DELIVERY_CHOICES, default='collect')
    house_no = models.CharField(max_length=50, blank=True)
    street = models.CharField(max_length=200, blank=True)
    area = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    mobile = models.CharField(max_length=15, blank=True)
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.application.get_short_id()} – {self.get_method_display()}"


class CourierTracking(models.Model):
    TRACKING_STATUS_CHOICES = [
        ('printed', 'Printed'),
        ('dispatched', 'Dispatched'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
    ]
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='tracking')
    courier_name = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True, db_index=True)
    dispatch_date = models.DateField(null=True, blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    tracking_status = models.CharField(max_length=20, choices=TRACKING_STATUS_CHOICES, default='printed')
    notes = models.TextField(blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.application.get_short_id()} – {self.tracking_number or 'No tracking'}"


class AdminAvailability(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('holiday', 'Holiday'),
        ('half_day', 'Half Day'),
    ]
    date = models.DateField(unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    notes = models.CharField(max_length=200, blank=True)
    set_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date']
        verbose_name_plural = 'Admin Availabilities'

    def __str__(self):
        return f"{self.date} – {self.get_status_display()}"
