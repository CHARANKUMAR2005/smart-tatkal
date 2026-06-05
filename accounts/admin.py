from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, StudentProfile, StaffProfile, AuditLog, Institution, College

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active']
    list_filter = ['role', 'is_active']
    fieldsets = UserAdmin.fieldsets + (('Role', {'fields': ('role', 'phone')}),)

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'student_id', 'department', 'year']
    search_fields = ['user__first_name', 'student_id']

@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'institution_type', 'city', 'state', 'is_active']
    list_filter = ['institution_type', 'state', 'is_active']
    search_fields = ['name', 'code', 'city', 'state']

@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ['college_name', 'college_code', 'university_name', 'state', 'district', 'is_active']
    list_filter = ['state', 'is_active']
    search_fields = ['college_name', 'college_code', 'university_name', 'state', 'district']

admin.site.register(StaffProfile)
admin.site.register(AuditLog)
