from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.core.mail import send_mail
from django.http import JsonResponse
from datetime import timedelta
import random

from .models import User, StudentProfile, StaffProfile, AuditLog, OTPVerification, College, Institution
from .forms import StudentRegistrationForm, StudentProfileForm, CustomLoginForm
from certificates.models import Application
from notifications.models import Notification

def log_action(user, action, details='', request=None):
    ip = request.META.get('REMOTE_ADDR') if request else None
    AuditLog.objects.create(user=user, action=action, details=details, ip_address=ip)


def send_sms(phone, message):
    try:
        from twilio.rest import Client
    except ImportError:
        if settings.DEBUG:
            print(f"[SMS fallback] To: {phone} | Message: {message}")
            return True
        return False

    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', '')

    if not (account_sid and auth_token and from_number):
        if settings.DEBUG:
            print(f"[SMS config missing] To: {phone} | Message: {message}")
            return True
        return False

    try:
        client = Client(account_sid, auth_token)
        client.messages.create(body=message, from_=from_number, to=phone)
        return True
    except Exception as exc:
        if settings.DEBUG:
            print(f"[SMS failed] {exc}")
        return False


def register_view(request):
    """
    :::comment::: Two-step registration with Gmail OTP verification.
    Step 1 (otp_step='form')   – User fills in the form; on POST we save
                                  form data to session and email an OTP.
    Step 2 (otp_step='verify') – User enters the 6-digit OTP; on match we
                                  create the account and log them in.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    context = {'otp_step': 'form'}

    if request.method == 'POST':
        action = request.POST.get('action', 'submit_form')

        # ── Step 1: validate form, persist to session, fire OTP ─────────────
        if action == 'submit_form':
            form = StudentRegistrationForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data['email']
                # :::comment::: Store cleaned data in session — no DB writes yet
                request.session['reg_form_data'] = {
                    'username':    form.cleaned_data['username'],
                    'first_name':  form.cleaned_data['first_name'],
                    'last_name':   form.cleaned_data['last_name'],
                    'email':       email,
                    'phone':       form.cleaned_data['phone'],
                    'password':    form.cleaned_data['password1'],
                    'student_id':  form.cleaned_data['student_id'],
                    'department':  form.cleaned_data['department'],
                    'year':        form.cleaned_data['year'],
                    'roll_number': form.cleaned_data.get('roll_number', ''),
                    'course':      form.cleaned_data.get('course', ''),
                }
                request.session['reg_email'] = email
                invalidate_previous_otps(email)
                otp_record = create_otp_record(email, None, 'email')
                sent = send_email_otp(email, otp_record.otp)
                if not sent:
                    messages.error(request, 'Could not send verification email. Please try again.')
                    return render(request, 'accounts/register.html', {'form': form, 'otp_step': 'form'})
                request.session['reg_otp_id'] = otp_record.pk
                messages.info(request, f'A 6-digit OTP has been sent to {email}. Please check your inbox.')
                return render(request, 'accounts/register.html', {
                    'otp_step': 'verify', 'masked_email': email
                })
            else:
                return render(request, 'accounts/register.html', {'form': form, 'otp_step': 'form'})

        # ── Step 2: verify OTP, create account ──────────────────────────────
        if action == 'verify_otp':
            otp_id    = request.session.get('reg_otp_id')
            email     = request.session.get('reg_email')
            entered   = request.POST.get('otp', '').strip()
            form_data = request.session.get('reg_form_data')

            if not all([otp_id, email, form_data]):
                messages.error(request, 'Session expired. Please fill the form again.')
                return redirect('register')

            otp_record = OTPVerification.objects.filter(
                pk=otp_id, email__iexact=email, is_active=True
            ).first()
            if not otp_record:
                messages.error(request, 'OTP session expired. Please start registration again.')
                return redirect('register')
            if timezone.now() > otp_record.expires_at:
                otp_record.invalidate()
                messages.error(request, 'OTP has expired. Please start registration again.')
                return redirect('register')
            if entered != otp_record.otp:
                otp_record.attempts = max(otp_record.attempts - 1, 0)
                otp_record.save()
                if otp_record.attempts <= 0:
                    otp_record.invalidate()
                    messages.error(request, 'Too many wrong attempts. Please start registration again.')
                    return redirect('register')
                messages.error(request, f'Incorrect OTP. {otp_record.attempts} attempt(s) remaining.')
                return render(request, 'accounts/register.html', {
                    'otp_step': 'verify', 'masked_email': email
                })

            # :::comment::: OTP verified — now create the user and profile
            otp_record.invalidate()
            user = User.objects.create_user(
                username=form_data['username'],
                email=form_data['email'],
                password=form_data['password'],
                first_name=form_data['first_name'],
                last_name=form_data['last_name'],
                role='student',
                is_email_verified=True,
            )
            user.phone = form_data['phone']
            user.save()
            StudentProfile.objects.create(
                user=user,
                student_id=form_data['student_id'],
                department=form_data['department'],
                year=form_data['year'],
                roll_number=form_data.get('roll_number', ''),
                course=form_data.get('course', ''),
            )
            Notification.objects.create(
                user=user, title='Welcome!',
                message=f'Welcome {user.first_name}! Your email has been verified and account created.',
                type='success'
            )
            log_action(user, 'REGISTER', 'New student registration – email OTP verified', request)
            for k in ['reg_form_data', 'reg_email', 'reg_otp_id']:
                request.session.pop(k, None)
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            messages.success(request, f'Registration successful! Welcome, {user.first_name}!')
            return redirect('dashboard')

        # ── Resend OTP during registration ───────────────────────────────────
        if action == 'resend_reg_otp':
            email  = request.session.get('reg_email')
            otp_id = request.session.get('reg_otp_id')
            if not email or not otp_id:
                messages.error(request, 'Session expired. Please fill the form again.')
                return redirect('register')
            existing = OTPVerification.objects.filter(pk=otp_id, is_active=True).first()
            if existing:
                if (timezone.now() - existing.last_sent_at).total_seconds() < 30:
                    wait = int(30 - (timezone.now() - existing.last_sent_at).total_seconds())
                    messages.warning(request, f'Please wait {wait}s before resending.')
                    return render(request, 'accounts/register.html', {
                        'otp_step': 'verify', 'masked_email': email
                    })
                existing.invalidate()
            new_otp = create_otp_record(email, None, 'email')
            send_email_otp(email, new_otp.otp)
            request.session['reg_otp_id'] = new_otp.pk
            messages.info(request, f'OTP resent to {email}.')
            return render(request, 'accounts/register.html', {
                'otp_step': 'verify', 'masked_email': email
            })

    # ── GET – show empty registration form ───────────────────────────────────
    context['form'] = StudentRegistrationForm()
    return render(request, 'accounts/register.html', context)


def generate_otp():
    return str(random.randint(100000, 999999)).zfill(6)


def send_email_otp(email, otp, purpose='login'):
    # :::comment::: Sends a styled OTP email via Gmail SMTP (or console in dev)
    subject = 'Your Tatkal CMS Verification Code'
    plain_message = (
        f'Your OTP is: {otp}\n'
        f'Valid for 5 minutes. Do not share this code with anyone.'
    )
    html_message = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0">
      <div style="background:linear-gradient(135deg,#0d1b3e,#1a4db5);padding:24px 32px;text-align:center">
        <h2 style="color:white;margin:0;font-size:1.3rem">Tatkal CMS – Email Verification</h2>
      </div>
      <div style="padding:28px 32px;text-align:center">
        <p style="color:#374151;font-size:1rem;margin-bottom:20px">
          Use the code below to {'verify your email and complete registration' if purpose == 'register' else 'sign in to your account'}.
        </p>
        <div style="background:#eff6ff;border:2px dashed #2563eb;border-radius:12px;padding:20px;display:inline-block;margin-bottom:20px">
          <span style="font-size:2.5rem;font-weight:900;letter-spacing:14px;color:#1a4db5">{otp}</span>
        </div>
        <p style="color:#64748b;font-size:0.85rem">Valid for <strong>5 minutes</strong>. Do not share this code with anyone.</p>
      </div>
      <div style="background:#f8fafc;padding:14px 32px;text-align:center;font-size:0.78rem;color:#94a3b8">
        If you did not request this, you can safely ignore this email.
      </div>
    </div>
    """
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tatkal.local')
    try:
        from django.core.mail import EmailMultiAlternatives
        msg = EmailMultiAlternatives(subject, plain_message, from_email, [email])
        msg.attach_alternative(html_message, 'text/html')
        msg.send(fail_silently=False)
        if settings.DEBUG:
            print(f'[Email OTP] To: {email} | OTP: {otp}')
        return True
    except Exception as exc:
        if settings.DEBUG:
            print(f'[Email failed] {exc}')
        return False

def send_approval_email(student_email, student_name, cert_type, app_id, short_id, status, remarks='', note=''):
    # Sends approved/rejected email - same method as OTP email above
    if status == 'approved':
        subject = f'Your {cert_type} Certificate is Approved - Tatkal CMS'
        status_line = 'APPROVED - Your certificate is ready to download.'
        color = '#1a7f37'
    else:
        subject = f'Your {cert_type} Application was Rejected - Tatkal CMS'
        status_line = 'REJECTED - Please contact the university office.'
        color = '#b91c1c'

    plain_message = (
        f'Dear {student_name},\n\n'
        f'Your {cert_type} application (#{short_id}) has been {status.upper()}.\n'
        f'{status_line}\n'
        + (f'Remarks: {remarks}\n' if remarks else '')
        + (f'Note: {note}\n' if note else '')
        + f'\nLogin: http://localhost:8000/applications/{app_id}/\n\nKakatiya University Tatkal CMS'
    )

    extra = ''
    if remarks:
        extra += f'<p style="background:#fff3cd;padding:10px;border-radius:6px"><b>Remarks:</b> {remarks}</p>'
    if note:
        extra += f'<p style="background:#fff3cd;padding:10px;border-radius:6px"><b>Note:</b> {note}</p>'

    html_message = f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0">
      <div style="background:{color};padding:24px 32px;text-align:center">
        <h2 style="color:white;margin:0;font-size:1.3rem">Kakatiya University - Tatkal CMS</h2>
      </div>
      <div style="padding:28px 32px">
        <p style="font-size:1rem;font-weight:700;color:{color}">Application {status.upper()}</p>
        <p style="color:#374151">Dear <strong>{student_name}</strong>,</p>
        <p style="color:#374151">Your <strong>{cert_type}</strong> application has been <strong>{status}</strong>.</p>
        {extra}
        <div style="background:#f8fafc;border-radius:8px;padding:14px;margin:16px 0;font-size:0.9rem">
          <b>Application ID:</b> #{short_id}<br>
          <b>Certificate:</b> {cert_type}
        </div>
        <a href="http://localhost:8000/applications/{app_id}/" style="display:inline-block;background:{color};color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:700">View Application</a>
      </div>
      <div style="background:#f8fafc;padding:12px 32px;text-align:center;font-size:0.78rem;color:#94a3b8">
        Automated message from Kakatiya University Tatkal CMS. Do not reply.
      </div>
    </div>
    """

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tatkal.local')
    try:
        from django.core.mail import EmailMultiAlternatives
        msg = EmailMultiAlternatives(subject, plain_message, from_email, [student_email])
        msg.attach_alternative(html_message, 'text/html')
        msg.send(fail_silently=False)
        if settings.DEBUG:
            print(f'[Approval Email] Sent {status} email to {student_email}')
        return True
    except Exception as exc:
        if settings.DEBUG:
            print(f'[Approval Email] Failed: {exc}')
        return False


def invalidate_previous_otps(email):
    OTPVerification.objects.filter(email__iexact=email, is_active=True).update(is_active=False)


def get_active_otp(email):
    return OTPVerification.objects.filter(email__iexact=email, is_active=True).order_by('-last_sent_at').first()


def create_otp_record(email, user, method):
    invalidate_previous_otps(email)
    otp_code = generate_otp()
    expires_at = timezone.now() + timedelta(minutes=5)
    return OTPVerification.objects.create(
        email=email,
        user=user,
        otp=otp_code,
        method=method,
        expires_at=expires_at,
        attempts=3,
        last_sent_at=timezone.now(),
        is_active=True,
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    context = {'otp_step': 'email'}

    if request.method == 'POST':
        action = request.POST.get('action', 'email')

        if action == 'email':
            email = request.POST.get('email', '').strip()
            if not email:
                messages.error(request, 'Please enter your email address.')
                return render(request, 'accounts/login.html', context)

            user = User.objects.filter(email__iexact=email).first()
            if not user:
                messages.error(request, 'No account found for that email address.')
                return render(request, 'accounts/login.html', context)

            request.session['otp_email'] = user.email
            request.session['otp_user_id'] = user.pk
            request.session['otp_stage'] = 'choose_method'
            request.session['otp_phone'] = f'****{user.phone[-4:]}' if user.phone and len(user.phone) >= 4 else None
            context.update({
                'otp_step': 'choose_method',
                'masked_phone': request.session['otp_phone'],
                'masked_email': user.email,
                'has_phone': bool(user.phone),
            })
            return render(request, 'accounts/login.html', context)

        if action == 'send_otp':
            email = request.session.get('otp_email')
            method = request.POST.get('method')
            user_id = request.session.get('otp_user_id')
            if not email or method not in ['phone', 'email'] or not user_id:
                messages.error(request, 'Unable to send OTP. Please start again.')
                return redirect('login')

            user = User.objects.filter(pk=user_id, email__iexact=email).first()
            if not user:
                messages.error(request, 'Unable to find your account. Please try again.')
                return redirect('login')

            if method == 'phone' and not user.phone:
                messages.error(request, 'No phone number available for this account.')
                return redirect('login')

            otp_record = create_otp_record(email, user, method)
            sent = False
            if method == 'phone':
                sent = send_sms(user.phone, f'Your OTP is {otp_record.otp}. Valid for 5 minutes.')
            else:
                sent = send_email_otp(user.email, otp_record.otp)

            if not sent:
                messages.error(request, 'Unable to send OTP right now. Please try again later.')
                return redirect('login')

            request.session['otp_method'] = method
            request.session['otp_stage'] = 'verify'
            request.session['otp_token_id'] = otp_record.pk
            request.session['otp_phone'] = f'****{user.phone[-4:]}' if user.phone and len(user.phone) >= 4 else None
            request.session['otp_sent_at'] = otp_record.last_sent_at.timestamp()

            context.update({
                'otp_step': 'verify',
                'masked_phone': request.session['otp_phone'],
                'masked_email': user.email,
                'otp_attempts': otp_record.attempts,
                'resend_available_in': 30,
                'selected_method': method,
            })
            messages.info(request, f'OTP sent via {method}.')
            return render(request, 'accounts/login.html', context)

        if action == 'verify_otp':
            email = request.session.get('otp_email')
            token_id = request.session.get('otp_token_id')
            entered_otp = request.POST.get('otp', '').strip()
            if not email or not token_id:
                messages.error(request, 'OTP session expired. Please start again.')
                return redirect('login')

            otp_record = OTPVerification.objects.filter(pk=token_id, email__iexact=email, is_active=True).first()
            if not otp_record:
                messages.error(request, 'OTP session expired. Please request a new code.')
                return redirect('login')

            if timezone.now() > otp_record.expires_at:
                otp_record.invalidate()
                messages.error(request, 'OTP expired. Please request a new one.')
                return redirect('login')

            if entered_otp != otp_record.otp:
                otp_record.attempts = max(otp_record.attempts - 1, 0)
                otp_record.save()
                if otp_record.attempts <= 0:
                    otp_record.invalidate()
                    messages.error(request, 'Invalid OTP. You have exceeded the maximum attempts.')
                    return redirect('login')
                messages.error(request, f'Invalid OTP. {otp_record.attempts} attempts remaining.')
                context.update({
                    'otp_step': 'verify',
                    'masked_phone': request.session.get('otp_phone'),
                    'masked_email': email,
                    'otp_attempts': otp_record.attempts,
                    'resend_available_in': max(0, 30 - int((timezone.now() - otp_record.last_sent_at).total_seconds())),
                    'selected_method': request.session.get('otp_method'),
                })
                return render(request, 'accounts/login.html', context)

            user = otp_record.user or User.objects.filter(email__iexact=email).first()
            if user:
                otp_record.invalidate()
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
                log_action(user, 'LOGIN', 'OTP verified', request)
                for key in ['otp_email', 'otp_user_id', 'otp_stage', 'otp_method', 'otp_token_id', 'otp_sent_at', 'otp_phone']:
                    request.session.pop(key, None)
                messages.success(request, f'Welcome back, {user.first_name}!')
                return redirect('dashboard')

            messages.error(request, 'Unable to verify login. Please try again.')
            return redirect('login')

        if action == 'resend_otp':
            email = request.session.get('otp_email')
            token_id = request.session.get('otp_token_id')
            if not email or not token_id:
                messages.error(request, 'Resend session expired. Please start again.')
                return redirect('login')

            otp_record = OTPVerification.objects.filter(pk=token_id, email__iexact=email, is_active=True).first()
            if not otp_record:
                messages.error(request, 'OTP session expired. Please request a new code.')
                return redirect('login')

            seconds_since_sent = (timezone.now() - otp_record.last_sent_at).total_seconds()
            if seconds_since_sent < 30:
                wait_seconds = int(30 - seconds_since_sent)
                messages.warning(request, f'Please wait {wait_seconds}s before resending OTP.')
                context.update({
                    'otp_step': 'verify',
                    'masked_phone': request.session.get('otp_phone'),
                    'masked_email': email,
                    'otp_attempts': otp_record.attempts,
                    'resend_available_in': wait_seconds,
                    'selected_method': request.session.get('otp_method'),
                })
                return render(request, 'accounts/login.html', context)

            user = User.objects.filter(email__iexact=email).first()
            if not user:
                messages.error(request, 'Unable to find account. Please try again.')
                return redirect('login')

            method = request.session.get('otp_method', 'email')
            otp_record.invalidate()
            new_record = create_otp_record(email, user, method)
            sent = False
            if method == 'phone':
                sent = send_sms(user.phone, f'Your OTP is {new_record.otp}. Valid for 5 minutes.')
            else:
                sent = send_email_otp(user.email, new_record.otp)

            if not sent:
                messages.error(request, 'Unable to resend OTP right now. Please try again later.')
                return redirect('login')

            request.session['otp_token_id'] = new_record.pk
            request.session['otp_sent_at'] = new_record.last_sent_at.timestamp()
            context.update({
                'otp_step': 'verify',
                'masked_phone': request.session.get('otp_phone'),
                'masked_email': email,
                'otp_attempts': new_record.attempts,
                'resend_available_in': 30,
                'selected_method': method,
            })
            messages.info(request, f'OTP resent to {method}.')
            return render(request, 'accounts/login.html', context)

    return render(request, 'accounts/login.html', context)

@login_required
def logout_view(request):
    log_action(request.user, 'LOGOUT', '', request)
    logout(request)
    return redirect('login')

@login_required
def dashboard_view(request):
    user = request.user
    context = {'user': user}
    
    if user.role == 'student':
        try:
            # Force fresh DB read — don't rely on Django's cached reverse accessor
            profile = StudentProfile.objects.select_related('user').get(user=user)
            applications = Application.objects.filter(student=profile)
            context.update({
                'profile': profile,
                'applications': applications[:5],
                'total_apps': applications.count(),
                'pending_apps': applications.filter(status__in=['submitted','under_verification','document_issue']).count(),
                'approved_apps': applications.filter(status__in=['approved','generated','delivered']).count(),
                'notifications': user.notifications.filter(is_read=False)[:5],
            })
        except StudentProfile.DoesNotExist:
            return redirect('profile_setup')
    
    elif user.role == 'staff':
        applications = Application.objects.all()
        context.update({
            'applications': applications.filter(status='submitted')[:10],
            'total_pending': applications.filter(status__in=['submitted','under_verification']).count(),
            'total_approved': applications.filter(status='approved').count(),
            'tatkal_pending': applications.filter(is_tatkal=True, status__in=['submitted','under_verification']).count(),
        })
    
    elif user.role == 'admin':
        from certificates.models import Certificate
        from payments.models import Payment
        from django.db.models import Sum
        applications = Application.objects.all()
        total_revenue = Payment.objects.filter(status='success').aggregate(Sum('amount'))['amount__sum'] or 0
        tatkal_revenue = Payment.objects.filter(status='success', application__is_tatkal=True).aggregate(Sum('amount'))['amount__sum'] or 0
        context.update({
            'total_applications': applications.count(),
            'pending_applications': applications.filter(status__in=['submitted','under_verification']).count(),
            'approved_applications': applications.filter(status__in=['approved','generated','delivered']).count(),
            'total_students': StudentProfile.objects.count(),
            'total_staff': StaffProfile.objects.count(),
            'total_revenue': total_revenue,
            'tatkal_revenue': tatkal_revenue,
            'recent_apps': applications[:10],
        })
    
    return render(request, f'dashboard/{user.role}_dashboard.html', context)

@login_required
def profile_view(request):
    user = request.user
    if user.role != 'student':
        return redirect('dashboard')

    # Always do a fresh DB read — never rely on cached accessor
    profile = StudentProfile.objects.filter(user=user).first()

    if request.method == 'POST':
        # --- Update User basic fields ---
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        phone      = request.POST.get('phone', '').strip()
        if first_name: user.first_name = first_name
        if last_name:  user.last_name  = last_name
        if phone:      user.phone      = phone
        user.save()

        # --- Validate required academic fields ---
        department = request.POST.get('department', '').strip()
        year_raw   = request.POST.get('year', '1').strip()
        if not department:
            messages.error(request, 'Department is required. Please select your department.')
            return render(request, 'accounts/profile.html', {
                'profile': profile,
                'dept_choices': StudentProfile.DEPT_CHOICES,
                'year_choices': StudentProfile.YEAR_CHOICES,
            })
        try:
            year = int(year_raw)
        except (ValueError, TypeError):
            year = 1

        # --- Build profile data dict from POST ---
        data = {
            'department':    department,
            'year':          year,
            'roll_number':   request.POST.get('roll_number', '').strip(),
            'course':        request.POST.get('course', '').strip(),
            'address':       request.POST.get('address', '').strip(),
            'father_name':   request.POST.get('father_name', '').strip(),
            'mother_name':   request.POST.get('mother_name', '').strip(),
            'aadhar_number': request.POST.get('aadhar_number', '').strip(),
        }
        # Optional fields
        dob = request.POST.get('date_of_birth', '').strip()
        if dob:
            data['date_of_birth'] = dob
        adm = request.POST.get('admission_year', '').strip()
        if adm and adm.isdigit():
            data['admission_year'] = int(adm)

        try:
            if profile:
                # Update existing profile
                for attr, val in data.items():
                    setattr(profile, attr, val)
                # Handle file uploads — only replace if a new file is submitted
                if 'profile_photo' in request.FILES:
                    profile.profile_photo = request.FILES['profile_photo']
                if 'id_card' in request.FILES:
                    profile.id_card = request.FILES['id_card']
                profile.save()
            else:
                # Create new profile — derive student_id from username
                student_id = user.username
                # Ensure uniqueness
                if StudentProfile.objects.filter(student_id=student_id).exclude(user=user).exists():
                    student_id = f"{user.username}_{user.pk}"
                profile = StudentProfile.objects.create(
                    user=user,
                    student_id=student_id,
                    **data,
                )
                if 'profile_photo' in request.FILES:
                    profile.profile_photo = request.FILES['profile_photo']
                    profile.save()
                if 'id_card' in request.FILES:
                    profile.id_card = request.FILES['id_card']
                    profile.save()

            log_action(user, 'PROFILE_UPDATE', 'Student profile saved', request)
            messages.success(request, '✅ Profile saved successfully!')
            return redirect('profile')

        except Exception as e:
            messages.error(request, f'Could not save profile: {e}')

    # Fresh read after redirect so displayed data is always current
    profile = StudentProfile.objects.filter(user=user).first()
    return render(request, 'accounts/profile.html', {
        'profile':      profile,
        'dept_choices': StudentProfile.DEPT_CHOICES,
        'year_choices': StudentProfile.YEAR_CHOICES,
    })

@login_required  
def profile_setup_view(request):
    # Prevent duplicate profile creation — use DB query, not cached attribute
    if StudentProfile.objects.filter(user=request.user).exists():
        return redirect('dashboard')

    if request.method == 'POST':
        form = StudentProfileForm(request.POST, request.FILES)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            # student_id is NOT on the form — derive it from user data
            # Priority: student_id from registration > username
            profile.student_id = (
                getattr(request.user, '_reg_student_id', None)
                or StudentProfile.objects.filter(user=request.user).values_list('student_id', flat=True).first()
                or request.user.username
            )
            try:
                profile.save()
                log_action(request.user, 'PROFILE_SETUP', 'Student profile created', request)
                messages.success(request, 'Profile setup complete!')
                return redirect('dashboard')
            except Exception as e:
                messages.error(request, f'Could not save profile: {e}')
        else:
            # Show form errors so the user knows what went wrong
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = StudentProfileForm()
    return render(request, 'accounts/profile_setup.html', {'form': form})

@login_required
def notifications_view(request):
    notifs = request.user.notifications.all()
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'accounts/notifications.html', {'notifications': notifs})

@login_required
def admin_users_view(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    students = StudentProfile.objects.select_related('user').all()
    staff = StaffProfile.objects.select_related('user').all()
    return render(request, 'admin/users.html', {'students': students, 'staff': staff})

@login_required
def audit_log_view(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:200]
    return render(request, 'admin/audit_log.html', {'logs': logs})

def college_search_api(request):
    """API endpoint for college/institution autocomplete search.

    GET parameters:
        q: search query
        page: page number

    Returns JSON with paginated results and type information.
    """
    query = request.GET.get('q', '').strip()
    page_number = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 0) or 0)

    if query:
        college_filters = (
            Q(college_name__icontains=query) |
            Q(college_code__icontains=query) |
            Q(university_name__icontains=query) |
            Q(state__icontains=query) |
            Q(district__icontains=query)
        )
        institution_filters = (
            Q(name__icontains=query) |
            Q(code__icontains=query) |
            Q(city__icontains=query) |
            Q(state__icontains=query)
        )
        college_qs = College.objects.filter(is_active=True).filter(college_filters).order_by('college_name')
        institution_qs = Institution.objects.filter(is_active=True).filter(institution_filters).order_by('name')
        if page_size <= 0:
            page_size = 20
    else:
        college_qs = College.objects.filter(is_active=True).order_by('college_name')
        institution_qs = Institution.objects.filter(is_active=True).order_by('name')
        if page_size <= 0:
            page_size = 1000

    results = []
    for college in college_qs:
        results.append({
            'id': str(college.pk),
            'type': 'college',
            'college_name': college.college_name,
            'college_code': college.college_code,
            'university_name': college.university_name,
            'state': college.state,
            'district': college.district,
        })
    for institution in institution_qs:
        results.append({
            'id': str(institution.pk),
            'type': 'institution',
            'college_name': institution.name,
            'college_code': institution.code,
            'university_name': '',
            'state': institution.state,
            'district': institution.city,
        })

    start = (page_number - 1) * page_size
    end = start + page_size
    page_results = results[start:end]
    has_next = end < len(results)

    return JsonResponse({
        'results': page_results,
        'page': int(page_number),
        'has_next': has_next,
    })
