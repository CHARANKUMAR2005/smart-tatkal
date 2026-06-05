from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Index
from django.db.models.functions import Lower
from django.utils import timezone
import uuid

class User(AbstractUser):
    ROLE_CHOICES = [('student', 'Student'), ('staff', 'Staff'), ('admin', 'Admin')]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    phone = models.CharField(max_length=15, blank=True)
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"

class Institution(models.Model):
    TYPE_CHOICES = [
        ('university', 'University'),
        ('college', 'College'),
    ]
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    institution_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='college')
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

class College(models.Model):
    college_code = models.CharField(max_length=50, unique=True)
    college_name = models.CharField(max_length=255, db_index=True)
    university_name = models.CharField(max_length=255, blank=True)
    state = models.CharField(max_length=100, blank=True, db_index=True)
    district = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['college_name']
        indexes = [
            Index(Lower('college_name'), name='college_name_lower_idx'),
            Index(Lower('college_code'), name='college_code_lower_idx'),
            Index(Lower('university_name'), name='university_name_lower_idx'),
        ]

    def __str__(self):
        return f"{self.college_name} ({self.college_code})"

class StudentProfile(models.Model):
    DEPT_CHOICES = [
        ('CSE', 'Computer Science'), ('ECE', 'Electronics'), ('MECH', 'Mechanical'),
        ('CIVIL', 'Civil'), ('EEE', 'Electrical'), ('IT', 'Information Technology'),
        ('MBA', 'Business Administration'), ('MCA', 'Computer Applications'),
    ]
    YEAR_CHOICES = [(i, f'{i} Year') for i in range(1, 6)]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField(max_length=20, unique=True)
    institution = models.ForeignKey(Institution, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.CharField(max_length=10, choices=DEPT_CHOICES)
    year = models.IntegerField(choices=YEAR_CHOICES, default=1)
    roll_number = models.CharField(max_length=20, blank=True)
    admission_year = models.IntegerField(null=True, blank=True)
    course = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    father_name = models.CharField(max_length=100, blank=True)
    mother_name = models.CharField(max_length=100, blank=True)
    aadhar_number = models.CharField(max_length=12, blank=True)
    profile_photo = models.ImageField(upload_to='profiles/', blank=True, null=True)
    id_card = models.FileField(upload_to='documents/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.student_id}"

class OTPVerification(models.Model):
    METHOD_CHOICES = [
        ('phone', 'Phone'),
        ('email', 'Email'),
    ]

    email = models.EmailField(db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    otp = models.CharField(max_length=6)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=3)
    last_sent_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-last_sent_at']

    def __str__(self):
        return f"OTP for {self.email} via {self.method}"

    def invalidate(self):
        self.is_active = False
        self.save()

    @property
    def remaining_time(self):
        return max(0, int((self.expires_at - timezone.now()).total_seconds()))

class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    staff_id = models.CharField(max_length=20, unique=True)
    designation = models.CharField(max_length=100)
    department = models.CharField(max_length=100, blank=True)
    can_approve = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.designation}"

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=200)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.action} at {self.timestamp}"
