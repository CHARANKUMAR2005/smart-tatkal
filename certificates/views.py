from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404, JsonResponse
from django.utils import timezone
from django.conf import settings
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Application, Certificate, ApplicationStatusHistory, CERTIFICATE_TYPES
from .utils import generate_verification_code, generate_qr_code, generate_certificate_pdf
from .emails import send_status_email, send_test_email
from accounts.models import StudentProfile, Institution, College
from accounts.views import send_approval_email
from notifications.models import Notification
from payments.models import Payment
import os

FEES = settings.NORMAL_FEE

def get_fee(cert_type, is_tatkal):
    base = FEES.get(cert_type, 100)
    return base * settings.TATKAL_MULTIPLIER if is_tatkal else base

@login_required
def apply_view(request):
    if request.user.role != 'student':
        return redirect('dashboard')
    try:
        profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        messages.error(request, 'Complete your profile first.')
        return redirect('profile_setup')
    
    cert_types = CERTIFICATE_TYPES
    if request.method == 'POST':
        cert_type = request.POST.get('certificate_type')
        college_id = request.POST.get('college')
        institution_id = request.POST.get('institution')
        college = College.objects.filter(pk=college_id).first() if college_id else None
        institution = Institution.objects.filter(pk=institution_id).first() if institution_id else None
        is_tatkal = request.POST.get('is_tatkal') == 'true'
        purpose = request.POST.get('purpose', '')
        
        # Duplicate check
        existing = Application.objects.filter(
            student=profile,
            certificate_type=cert_type,
            status__in=['submitted', 'under_verification', 'approved']
        ).first()
        if existing:
            messages.warning(request, f'You already have a pending {existing.get_certificate_type_display()} application.')
            return redirect('my_applications')
        
        fee = get_fee(cert_type, is_tatkal)
        
        app = Application.objects.create(
            student=profile,
            certificate_type=cert_type,
            college=college,
            institution=institution,
            is_tatkal=is_tatkal,
            purpose=purpose,
            fee_amount=fee,
        )
        
        # Handle document uploads
        for i, field in enumerate(['document1', 'document2', 'document3'], 1):
            doc = request.FILES.get(f'document{i}')
            if doc:
                setattr(app, field, doc)
        app.save()
        
        ApplicationStatusHistory.objects.create(
            application=app, from_status='', to_status='submitted',
            changed_by=request.user, note='Application submitted by student.'
        )
        
        Notification.objects.create(
            user=request.user, title='Application Submitted',
            message=f'Your {app.get_certificate_type_display()} application (#{app.get_short_id()}) has been submitted successfully.',
            type='success', link=f'/applications/{app.application_id}/'
        )
        
        messages.success(request, f'Application submitted! ID: #{app.get_short_id()}')
        return redirect('payment', app_id=app.application_id)
    
    return render(request, 'certificates/apply.html', {
        'cert_types': cert_types,
        'profile': profile,
        'fees': FEES,
        'tatkal_multiplier': settings.TATKAL_MULTIPLIER,
    })

@login_required
def my_applications_view(request):
    if request.user.role != 'student':
        return redirect('dashboard')
    try:
        profile = request.user.student_profile
    except:
        return redirect('profile_setup')
    
    apps = Application.objects.filter(student=profile).select_related('student')
    return render(request, 'certificates/my_applications.html', {'applications': apps})

@login_required
def application_detail_view(request, app_id):
    app = get_object_or_404(Application, application_id=app_id)
    if request.user.role == 'student' and app.student.user != request.user:
        raise Http404
    
    history = app.status_history.select_related('changed_by').all()
    cert = getattr(app, 'certificate', None)
    payment = getattr(app, 'payment', None)
    
    return render(request, 'certificates/application_detail.html', {
        'application': app, 'history': history, 'certificate': cert, 'payment': payment
    })

@login_required
def staff_applications_view(request):
    if request.user.role not in ('staff', 'admin'):
        return redirect('dashboard')
    
    apps = Application.objects.select_related('student__user').all()
    status_filter = request.GET.get('status', '')
    if status_filter:
        apps = apps.filter(status=status_filter)
    
    sort = request.GET.get('sort', '-created_at')
    if sort == 'tatkal':
        apps = apps.order_by('-is_tatkal', '-created_at')
    else:
        apps = apps.order_by(sort)
    
    return render(request, 'certificates/staff_applications.html', {
        'applications': apps, 'status_filter': status_filter
    })

@login_required
def update_status_view(request, app_id):
    if request.user.role not in ('staff', 'admin'):
        return redirect('dashboard')
    
    app = get_object_or_404(Application, application_id=app_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        note = request.POST.get('note', '')
        staff_remarks = request.POST.get('staff_remarks', '')
        
        old_status = app.status
        app.status = new_status
        if staff_remarks:
            app.staff_remarks = staff_remarks
        
        if new_status == 'approved':
            app.processed_at = timezone.now()
            # Generate certificate
            cert = Certificate.objects.create(
                application=app,
                verification_code=generate_verification_code(),
                issued_by=request.user
            )
            verify_url = f"{settings.BASE_URL}/verify/{cert.verification_code}/"
            qr_filename = f"qr_{cert.verification_code}.png"
            cert.qr_code = generate_qr_code(verify_url, qr_filename)
            cert.pdf_path = generate_certificate_pdf(app, cert)
            cert.save()
            app.status = 'generated'
        
        app.save()
        
        ApplicationStatusHistory.objects.create(
            application=app, from_status=old_status, to_status=app.status,
            changed_by=request.user, note=note
        )
        
        Notification.objects.create(
            user=app.student.user,
            title=f'Application Status Updated',
            message=f'Your {app.get_certificate_type_display()} application status: {app.get_status_display()}. {note}',
            type='success' if app.status in ('approved','generated') else ('warning' if app.status == 'document_issue' else 'error'),
            link=f'/applications/{app.application_id}/'
        )

        # Send email to student
        if new_status in ('approved', 'rejected'):
            send_approval_email(
                student_email=app.student.user.email,
                student_name=app.student.user.get_full_name() or app.student.user.username,
                cert_type=app.get_certificate_type_display(),
                app_id=app.application_id,
                short_id=app.get_short_id(),
                status=new_status,
                remarks=staff_remarks,
                note=note,
            )

        messages.success(request, f'Application status updated to: {app.get_status_display()}')
        return redirect('application_detail', app_id=app_id)
    
    return render(request, 'certificates/update_status.html', {'application': app})

@login_required
def download_certificate_view(request, cert_id):
    from django.core.files.storage import default_storage

    cert = get_object_or_404(Certificate, certificate_id=cert_id)
    if request.user.role == 'student' and cert.application.student.user != request.user:
        raise Http404

    # Check whether the stored file is still accessible (ephemeral Render storage
    # loses local files on every redeploy; Cloudinary always returns True).
    file_missing = True
    if cert.pdf_path:
        try:
            file_missing = not default_storage.exists(cert.pdf_path.name)
        except Exception:
            file_missing = True

    if file_missing:
        try:
            verify_url = f"{settings.BASE_URL}/verify/{cert.verification_code}/"
            cert.qr_code = generate_qr_code(verify_url, f"qr_{cert.verification_code}.png")
            cert.pdf_path = generate_certificate_pdf(cert.application, cert)
            cert.save()
        except Exception as exc:
            messages.error(request, f'Could not generate certificate: {exc}')
            return redirect('application_detail', app_id=cert.application.application_id)

    cert.download_count += 1
    cert.save()

    # Redirect to storage URL — works for both local /media/ and Cloudinary CDN.
    try:
        return redirect(cert.pdf_path.url)
    except Exception:
        # Fallback: stream directly (local dev without media serving configured)
        try:
            f = default_storage.open(cert.pdf_path.name)
            return FileResponse(f, as_attachment=True,
                                filename=f"Certificate_{cert.verification_code}.pdf")
        except Exception as exc:
            messages.error(request, f'Could not serve certificate: {exc}')
            return redirect('application_detail', app_id=cert.application.application_id)

def verify_certificate_view(request, code):
    try:
        cert = Certificate.objects.select_related('application__student__user').get(verification_code=code)
        return render(request, 'certificates/verify.html', {'certificate': cert, 'valid': cert.is_valid})
    except Certificate.DoesNotExist:
        return render(request, 'certificates/verify.html', {'valid': False, 'code': code})

@login_required
def college_search_api(request):
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
    seen_results = set()
    for college in college_qs:
        # Key on name+code only (no type prefix) so a college in both tables is deduplicated
        key = (college.college_name.strip().lower(), college.college_code.strip().lower())
        if key in seen_results:
            continue
        seen_results.add(key)
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
        key = (institution.name.strip().lower(), institution.code.strip().lower())
        if key in seen_results:
            continue
        seen_results.add(key)
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

@login_required
def get_fee_ajax(request):
    cert_type = request.GET.get('type')
    is_tatkal = request.GET.get('tatkal') == 'true'
    fee = get_fee(cert_type, is_tatkal)
    return JsonResponse({'fee': fee, 'is_tatkal': is_tatkal})


@login_required
def test_email_view(request):
    """Admin-only page to test SMTP email configuration."""
    if request.user.role not in ('admin', 'staff'):
        return redirect('dashboard')

    result = None
    if request.method == 'POST':
        to_email = request.POST.get('to_email', '').strip() or request.user.email
        success, message = send_test_email(to_email)
        result = {'success': success, 'message': message, 'to_email': to_email}

    return render(request, 'certificates/test_email.html', {
        'result': result,
        'user_email': request.user.email,
        'email_backend': __import__('django.conf', fromlist=['settings']).settings.EMAIL_BACKEND,
        'email_host_user': __import__('django.conf', fromlist=['settings']).settings.EMAIL_HOST_USER,
    })
