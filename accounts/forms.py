from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, StudentProfile

class StudentRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=True)
    student_id = forms.CharField(max_length=20, required=True, label='Student ID / Hall Ticket Number')
    department = forms.ChoiceField(choices=StudentProfile.DEPT_CHOICES)
    year = forms.ChoiceField(choices=StudentProfile.YEAR_CHOICES)
    roll_number = forms.CharField(max_length=20, required=False)
    course = forms.CharField(max_length=100, required=False)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already registered.")
        return email

    def clean_student_id(self):
        sid = self.cleaned_data.get('student_id')
        if StudentProfile.objects.filter(student_id=sid).exists():
            raise forms.ValidationError("Student ID already registered.")
        return sid

class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['institution', 'department', 'year', 'roll_number', 'course', 'admission_year',
                  'address', 'date_of_birth', 'father_name', 'mother_name',
                  'aadhar_number', 'profile_photo', 'id_card']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
            'profile_photo': forms.ClearableFileInput(),
            'id_card': forms.ClearableFileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}),
        }
        labels = {
            'profile_photo': 'Profile Photo',
            'id_card': 'ID Card / Supporting Document',
        }
        help_texts = {
            'profile_photo': 'Upload a clear profile photo (JPEG, PNG).',
            'id_card': 'Upload a valid student ID, Aadhar, or fee receipt.',
        }

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(label='Username or Email')
