from django.db import models
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
