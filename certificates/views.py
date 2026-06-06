from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404, JsonResponse
from django.utils import timezone
from django.conf import settings
from django.db.models import Q
from django.core.paginator import Paginator
from .models import (Application, Certificate, ApplicationStatusHistory, CERTIFICATE_TYPES,
                     DeliveryDetails, CourierTracking, AdminAvailability, SlotBooking)
from .utils import generate_verification_code, generate_qr_code, generate_certificate_pdf
from .emails import send_status_email, send_test_email
from accounts.models import StudentProfile, Institution, College
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
    delivery_fee = settings.DELIVERY_FEE

    if request.method == 'POST':
        cert_type = request.POST.get('certificate_type')
        college_id = request.POST.get('college')
        institution_id = request.POST.get('institution')
        college = College.objects.filter(pk=college_id).first() if college_id else None
        institution = Institution.objects.filter(pk=institution_id).first() if institution_id else None
        is_tatkal = request.POST.get('is_tatkal') == 'true'
        purpose = request.POST.get('purpose', '')
        delivery_method = request.POST.get('delivery_method', 'collect')

        existing = Application.objects.filter(
            student=profile,
            certificate_type=cert_type,
            status__in=['submitted', 'under_verification', 'approved']
        ).first()
        if existing:
            messages.warning(request, f'You already have a pending {existing.get_certificate_type_display()} application.')
            return redirect('my_applications')

        cert_fee = get_fee(cert_type, is_tatkal)
        d_fee = delivery_fee if delivery_method == 'home' else 0
        total_fee = cert_fee + d_fee

        app = Application.objects.create(
            student=profile,
            certificate_type=cert_type,
            college=college,
            institution=institution,
            is_tatkal=is_tatkal,
            purpose=purpose,
            fee_amount=total_fee,
        )

        for field in ['document1', 'document2', 'document3']:
            doc = request.FILES.get(field)
            if doc:
                setattr(app, field, doc)
        app.save()

        dd = DeliveryDetails(application=app, method=delivery_method, delivery_fee=d_fee)
        if delivery_method == 'home':
            dd.house_no = request.POST.get('house_no', '')
            dd.street = request.POST.get('street', '')
            dd.area = request.POST.get('area', '')
            dd.city = request.POST.get('city', '')
            dd.state = request.POST.get('del_state', '')
            dd.pincode = request.POST.get('pincode', '')
            dd.mobile = request.POST.get('delivery_mobile', '')
        dd.save()

        ApplicationStatusHistory.objects.create(
            application=app, from_status='', to_status='submitted',
            changed_by=request.user, note='Application submitted by student.'
        )
        Notification.objects.create(
            user=request.user, title='Application Submitted',
            message=f'Your {app.get_certificate_type_display()} application (#{app.get_short_id()}) has been submitted.',
            type='success', link=f'/applications/{app.application_id}/'
        )
        messages.success(request, f'Application submitted! ID: #{app.get_short_id()}')
        return redirect('payment', app_id=app.application_id)

    return render(request, 'certificates/apply.html', {
        'cert_types': cert_types,
        'profile': profile,
        'fees': FEES,
        'tatkal_multiplier': settings.TATKAL_MULTIPLIER,
        'delivery_fee': delivery_fee,
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
    delivery = getattr(app, 'delivery', None)
    tracking = getattr(app, 'tracking', None)

    return render(request, 'certificates/application_detail.html', {
        'application': app, 'history': history, 'certificate': cert,
        'payment': payment, 'delivery': delivery, 'tracking': tracking,
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

        courier_name = request.POST.get('courier_name', '').strip()
        tracking_number = request.POST.get('tracking_number', '').strip()
        dispatch_date_str = request.POST.get('dispatch_date', '').strip()
        expected_delivery_str = request.POST.get('expected_delivery_date', '').strip()
        tracking_status = request.POST.get('tracking_status', '').strip()
        tracking_notes = request.POST.get('tracking_notes', '').strip()

        old_status = app.status
        app.status = new_status
        if staff_remarks:
            app.staff_remarks = staff_remarks

        if new_status == 'approved':
            app.processed_at = timezone.now()
            cert = Certificate.objects.create(
                application=app,
                verification_code=generate_verification_code(),
                issued_by=request.user
            )
            verify_url = f"{settings.BASE_URL}/verify/{cert.verification_code}/"
            cert.qr_code = generate_qr_code(verify_url, f"qr_{cert.verification_code}.png")
            cert.pdf_path = generate_certificate_pdf(app, cert)
            cert.save()
            app.status = 'generated'

        app.save()

        if any([courier_name, tracking_number, dispatch_date_str, expected_delivery_str, tracking_status]):
            from datetime import date as date_type
            tracking_obj, _ = CourierTracking.objects.get_or_create(application=app)
            if courier_name:
                tracking_obj.courier_name = courier_name
            if tracking_number:
                tracking_obj.tracking_number = tracking_number
            if dispatch_date_str:
                try:
                    tracking_obj.dispatch_date = date_type.fromisoformat(dispatch_date_str)
                except ValueError:
                    pass
            if expected_delivery_str:
                try:
                    tracking_obj.expected_delivery_date = date_type.fromisoformat(expected_delivery_str)
                except ValueError:
                    pass
            if tracking_status:
                tracking_obj.tracking_status = tracking_status
            if tracking_notes:
                tracking_obj.notes = tracking_notes
            tracking_obj.updated_by = request.user
            tracking_obj.save()

        ApplicationStatusHistory.objects.create(
            application=app, from_status=old_status, to_status=app.status,
            changed_by=request.user, note=note
        )
        Notification.objects.create(
            user=app.student.user,
            title='Application Status Updated',
            message=f'Your {app.get_certificate_type_display()} application status: {app.get_status_display()}. {note}',
            type='success' if app.status in ('approved', 'generated') else ('warning' if app.status == 'document_issue' else 'error'),
            link=f'/applications/{app.application_id}/'
        )

        email_ok = send_status_email(app, new_status, note=note, staff_remarks=staff_remarks)
        messages.success(request, f'Application status updated to: {app.get_status_display()}')
        if new_status in ('approved', 'rejected') and not email_ok:
            messages.warning(
                request,
                f'Status saved, but the email to {app.student.user.email} failed — '
                f'check Render logs and SENDER_EMAIL env var.'
            )
        return redirect('application_detail', app_id=app_id)

    tracking = getattr(app, 'tracking', None)
    return render(request, 'certificates/update_status.html', {
        'application': app, 'tracking': tracking,
    })

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


# ─── Public Certificate Tracking ─────────────────────────────────────────────

def track_certificate_view(request):
    result = None
    error = None
    query = (request.POST.get('query') or request.GET.get('q', '')).strip()

    if query:
        try:
            tracking_obj = CourierTracking.objects.select_related(
                'application__student__user', 'application__delivery'
            ).get(tracking_number__iexact=query)
            result = tracking_obj.application
        except CourierTracking.DoesNotExist:
            pass

        if not result:
            try:
                from uuid import UUID
                result = Application.objects.select_related('student__user').get(
                    application_id=UUID(query)
                )
            except (Application.DoesNotExist, ValueError):
                pass

        if not result:
            apps = Application.objects.select_related('student__user').filter(
                application_id__startswith=query.lower()
            )
            if apps.count() == 1:
                result = apps.first()

        if not result:
            error = f'No application found for "{query}". Please check your Application ID or Tracking Number.'

    status_steps = [
        ('submitted', '📋', 'Submitted'),
        ('under_verification', '🔍', 'Verifying'),
        ('approved', '✅', 'Approved'),
        ('generated', '📄', 'Generated'),
        ('delivered', '🎉', 'Delivered'),
    ]
    return render(request, 'certificates/track.html', {
        'result': result,
        'error': error,
        'query': query,
        'statuses': status_steps,
        'tracking': getattr(result, 'tracking', None) if result else None,
        'delivery': getattr(result, 'delivery', None) if result else None,
    })


# ─── Analytics Dashboard ──────────────────────────────────────────────────────

@login_required
def analytics_view(request):
    if request.user.role not in ('staff', 'admin'):
        return redirect('dashboard')

    from django.db.models import Count, Sum
    from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
    from datetime import date, timedelta

    today = date.today()
    thirty_ago = today - timedelta(days=29)
    eight_weeks_ago = today - timedelta(weeks=8)

    today_apps = Application.objects.filter(created_at__date=today)
    stats_today = {
        'total': today_apps.count(),
        'pending': today_apps.filter(status__in=['submitted', 'under_verification']).count(),
        'approved': today_apps.filter(status__in=['approved', 'generated']).count(),
        'rejected': today_apps.filter(status='rejected').count(),
        'delivered': today_apps.filter(status='delivered').count(),
    }

    daily_qs = (
        Application.objects.filter(created_at__date__gte=thirty_ago)
        .annotate(day=TruncDate('created_at'))
        .values('day').annotate(count=Count('id')).order_by('day')
    )
    daily_data = {item['day']: item['count'] for item in daily_qs}

    days_list = []
    for i in range(30):
        d = thirty_ago + timedelta(days=i)
        count = daily_data.get(d, 0)
        crowd = 'none' if count == 0 else 'low' if count <= 20 else 'medium' if count <= 50 else 'high' if count <= 100 else 'very_high'
        days_list.append({'date': d, 'count': count, 'crowd': crowd,
                          'label': d.strftime('%d %b')})

    non_zero = [d for d in days_list if d['count'] > 0]
    busiest = max(non_zero, key=lambda x: x['count']) if non_zero else None
    least_busy = min(non_zero, key=lambda x: x['count']) if non_zero else None
    avg_per_day = round(sum(d['count'] for d in days_list) / 30, 1)

    weekly_qs = (
        Application.objects.filter(created_at__date__gte=eight_weeks_ago)
        .annotate(week=TruncWeek('created_at'))
        .values('week').annotate(count=Count('id')).order_by('week')
    )
    monthly_qs = (
        Application.objects.filter(created_at__date__gte=today - timedelta(days=180))
        .annotate(month=TruncMonth('created_at'))
        .values('month').annotate(count=Count('id')).order_by('month')
    )

    cert_breakdown = list(
        Application.objects.values('certificate_type')
        .annotate(count=Count('id')).order_by('-count')
    )
    for item in cert_breakdown:
        item['label'] = dict(CERTIFICATE_TYPES).get(item['certificate_type'], item['certificate_type'])

    status_breakdown = list(
        Application.objects.values('status').annotate(count=Count('id')).order_by('-count')
    )

    delivery_stats = {
        'home': Application.objects.filter(delivery__method='home').count(),
        'collect': Application.objects.filter(delivery__method='collect').count(),
        'no_selection': Application.objects.filter(delivery__isnull=True).count(),
    }

    return render(request, 'certificates/analytics.html', {
        'stats_today': stats_today,
        'days_list': days_list,
        'busiest': busiest,
        'least_busy': least_busy,
        'avg_per_day': avg_per_day,
        'weekly_counts': list(weekly_qs),
        'monthly_counts': list(monthly_qs),
        'cert_breakdown': cert_breakdown,
        'status_breakdown': status_breakdown,
        'delivery_stats': delivery_stats,
        'today': today,
    })


# ─── Admin Availability Calendar ─────────────────────────────────────────────

@login_required
def admin_availability_view(request):
    if request.user.role not in ('staff', 'admin'):
        return redirect('dashboard')

    import calendar as cal_module
    from datetime import date, timedelta

    if request.method == 'POST':
        action = request.POST.get('action')
        date_str = request.POST.get('date', '')
        try:
            d = date.fromisoformat(date_str)
        except (ValueError, TypeError):
            messages.error(request, 'Invalid date.')
            return redirect('admin_availability')

        if action == 'set':
            AdminAvailability.objects.update_or_create(
                date=d,
                defaults={
                    'status': request.POST.get('status', 'available'),
                    'notes': request.POST.get('notes', ''),
                    'set_by': request.user,
                }
            )
            messages.success(request, f'Availability for {d.strftime("%d %b %Y")} saved.')
        elif action == 'delete':
            AdminAvailability.objects.filter(date=d).delete()
            messages.success(request, f'Availability for {d.strftime("%d %b %Y")} cleared.')

        return redirect('admin_availability')

    from django.db.models import Count
    from django.db.models.functions import TruncDate

    today = date.today()
    end_date = today + timedelta(days=90)

    avail_map = {a.date: a for a in AdminAvailability.objects.filter(date__gte=today, date__lte=end_date)}
    count_map = {
        item['day']: item['count']
        for item in Application.objects.filter(created_at__date__gte=today, created_at__date__lte=end_date)
        .annotate(day=TruncDate('created_at')).values('day').annotate(count=Count('id'))
    }

    months = []
    for mo in range(3):
        y, m = today.year, today.month + mo
        if m > 12:
            m -= 12; y += 1
        weeks_raw = cal_module.monthcalendar(y, m)
        weeks = []
        for week in weeks_raw:
            days = []
            for dn in week:
                if dn == 0:
                    days.append(None)
                else:
                    d = date(y, m, dn)
                    avail = avail_map.get(d)
                    cnt = count_map.get(d, 0)
                    crowd = 'none' if cnt == 0 else 'low' if cnt <= 20 else 'medium' if cnt <= 50 else 'high' if cnt <= 100 else 'very_high'
                    days.append({'date': d, 'dn': dn, 'avail': avail,
                                 'crowd_count': cnt, 'crowd': crowd,
                                 'past': d < today, 'today': d == today})
            weeks.append(days)
        months.append({'name': date(y, m, 1).strftime('%B %Y'), 'weeks': weeks})

    recommendations = []
    for i in range(60):
        d = today + timedelta(days=i + 1)
        if d.weekday() >= 5:
            continue
        avail = avail_map.get(d)
        if avail and avail.status in ('holiday', 'busy'):
            continue
        if count_map.get(d, 0) <= 20:
            recommendations.append({
                'date': d,
                'crowd': count_map.get(d, 0),
                'avail_status': avail.status if avail else 'available',
                'notes': avail.notes if avail else '',
            })
        if len(recommendations) >= 3:
            break

    return render(request, 'certificates/availability_calendar.html', {
        'months': months,
        'recommendations': recommendations,
        'today': today,
    })


# ─── Reports ─────────────────────────────────────────────────────────────────

@login_required
def reports_view(request):
    if request.user.role not in ('staff', 'admin'):
        return redirect('dashboard')

    from datetime import date, timedelta
    today = date.today()
    period = request.GET.get('period', 'daily')
    report_type = request.GET.get('type', '')
    export_fmt = request.GET.get('format', '')

    if period == 'weekly':
        start_date = today - timedelta(days=7)
    elif period == 'monthly':
        start_date = today.replace(day=1)
    else:
        start_date = today

    if export_fmt in ('pdf', 'excel') and report_type:
        return _generate_report(request, report_type, period, start_date, today, export_fmt)

    from django.db.models import Count, Sum
    summary = {
        'total': Application.objects.filter(created_at__date__gte=start_date).count(),
        'approved': Application.objects.filter(created_at__date__gte=start_date, status__in=['approved', 'generated', 'delivered']).count(),
        'rejected': Application.objects.filter(created_at__date__gte=start_date, status='rejected').count(),
        'home_delivery': Application.objects.filter(created_at__date__gte=start_date, delivery__method='home').count(),
        'revenue': Application.objects.filter(created_at__date__gte=start_date, payment_status='paid').aggregate(t=Sum('fee_amount'))['t'] or 0,
    }
    return render(request, 'certificates/reports.html', {
        'today': today, 'period': period, 'start_date': start_date, 'summary': summary,
    })


def _generate_report(request, report_type, period, start_date, end_date, fmt):
    import io as _io
    from django.http import HttpResponse
    from django.db.models import Count, Sum

    apps = Application.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).select_related('student__user', 'delivery', 'tracking')

    if report_type == 'delivery':
        apps = apps.filter(delivery__method='home')

    period_label = period.title()
    filename_base = f"{report_type}_{period}_report"

    if fmt == 'excel':
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
        except ImportError:
            messages.error(request, 'openpyxl not installed. Run: pip install openpyxl')
            return redirect('reports')

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f'{period_label} Report'

        header_font = Font(bold=True, color='FFFFFF')
        header_fill = PatternFill('solid', fgColor='0D1B3E')

        if report_type == 'delivery':
            headers = ['App ID', 'Student', 'Cert Type', 'Delivery Method',
                       'City', 'State', 'Pincode', 'Mobile', 'Courier', 'Tracking No',
                       'Dispatch Date', 'Expected Delivery', 'Track Status']
        elif report_type == 'crowd':
            from django.db.models.functions import TruncDate
            daily = (Application.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
                     .annotate(day=TruncDate('created_at')).values('day').annotate(count=Count('id')).order_by('day'))
            headers = ['Date', 'Applications', 'Crowd Level']
            ws.append(headers)
            for c, cell in enumerate(ws[1], 1):
                cell.font = header_font; cell.fill = header_fill
            for row in daily:
                cnt = row['count']
                crowd = 'Low' if cnt <= 20 else 'Medium' if cnt <= 50 else 'High' if cnt <= 100 else 'Very High'
                ws.append([row['day'].strftime('%d %b %Y'), cnt, crowd])
            buf = _io.BytesIO(); wb.save(buf); buf.seek(0)
            resp = HttpResponse(buf.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            resp['Content-Disposition'] = f'attachment; filename="{filename_base}.xlsx"'
            return resp
        else:
            headers = ['App ID', 'Student', 'Student ID', 'Cert Type', 'Service',
                       'Status', 'Payment', 'Fee (₹)', 'Date']

        ws.append(headers)
        for c, cell in enumerate(ws[1], 1):
            cell.font = header_font; cell.fill = header_fill; cell.alignment = Alignment(horizontal='center')

        for app in apps:
            delivery = getattr(app, 'delivery', None)
            tracking = getattr(app, 'tracking', None)
            if report_type == 'delivery':
                ws.append([
                    app.get_short_id(),
                    app.student.user.get_full_name(),
                    app.get_certificate_type_display(),
                    delivery.get_method_display() if delivery else '—',
                    delivery.city if delivery else '—',
                    delivery.state if delivery else '—',
                    delivery.pincode if delivery else '—',
                    delivery.mobile if delivery else '—',
                    tracking.courier_name if tracking else '—',
                    tracking.tracking_number if tracking else '—',
                    tracking.dispatch_date.strftime('%d %b %Y') if tracking and tracking.dispatch_date else '—',
                    tracking.expected_delivery_date.strftime('%d %b %Y') if tracking and tracking.expected_delivery_date else '—',
                    tracking.get_tracking_status_display() if tracking else '—',
                ])
            else:
                ws.append([
                    app.get_short_id(),
                    app.student.user.get_full_name(),
                    app.student.student_id,
                    app.get_certificate_type_display(),
                    'TATKAL' if app.is_tatkal else 'Normal',
                    app.get_status_display(),
                    app.payment_status.title(),
                    float(app.fee_amount),
                    app.created_at.strftime('%d %b %Y'),
                ])

        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 18

        buf = _io.BytesIO(); wb.save(buf); buf.seek(0)
        resp = HttpResponse(buf.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp['Content-Disposition'] = f'attachment; filename="{filename_base}.xlsx"'
        return resp

    # PDF report
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm

    buf = _io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4) if report_type == 'delivery' else A4,
                            topMargin=15*mm, bottomMargin=15*mm, leftMargin=15*mm, rightMargin=15*mm)
    styles = getSampleStyleSheet()
    story = []

    title = Paragraph(f"<b>{settings.UNIVERSITY_NAME}</b>", styles['Title'])
    subtitle = Paragraph(f"{period_label} {report_type.title()} Report | {start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')}", styles['Normal'])
    story += [title, subtitle, Spacer(1, 10*mm)]

    if report_type == 'crowd':
        from django.db.models.functions import TruncDate
        daily = (Application.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
                 .annotate(day=TruncDate('created_at')).values('day').annotate(count=Count('id')).order_by('day'))
        data = [['Date', 'Applications', 'Crowd Level']]
        for row in daily:
            cnt = row['count']
            crowd = 'Low' if cnt <= 20 else 'Medium' if cnt <= 50 else 'High' if cnt <= 100 else 'Very High'
            data.append([row['day'].strftime('%d %b %Y'), str(cnt), crowd])
    elif report_type == 'delivery':
        data = [['App ID', 'Student', 'City', 'State', 'Courier', 'Tracking No', 'Track Status']]
        for app in apps:
            delivery = getattr(app, 'delivery', None)
            tracking = getattr(app, 'tracking', None)
            data.append([
                app.get_short_id(),
                app.student.user.get_full_name()[:20],
                delivery.city if delivery else '—',
                delivery.state if delivery else '—',
                tracking.courier_name if tracking else '—',
                tracking.tracking_number if tracking else '—',
                tracking.get_tracking_status_display() if tracking else '—',
            ])
    else:
        data = [['App ID', 'Student', 'Certificate', 'Service', 'Status', 'Fee']]
        for app in apps:
            data.append([
                app.get_short_id(),
                app.student.user.get_full_name()[:22],
                app.get_certificate_type_display()[:20],
                'TATKAL' if app.is_tatkal else 'Normal',
                app.get_status_display(),
                f'Rs.{app.fee_amount}',
            ])

    col_count = len(data[0])
    available_width = (landscape(A4)[0] if report_type == 'delivery' else A4[0]) - 30*mm
    col_w = available_width / col_count

    tbl = Table(data, colWidths=[col_w] * col_count)
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0D1B3E')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(tbl)
    doc.build(story)
    buf.seek(0)

    resp = HttpResponse(buf.read(), content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="{filename_base}.pdf"'
    return resp


# ─── Slot Booking / Crowd Page ───────────────────────────────────────────────

@login_required
def slot_booking_view(request):
    from datetime import date as date_cls, timedelta
    from collections import defaultdict

    today = date_cls.today()
    now = timezone.localtime(timezone.now())

    # Build next 7 working days starting from today
    working_days = []
    d = today
    while len(working_days) < 7:
        if d.weekday() < 5:
            working_days.append(d)
        d += timedelta(days=1)

    # Resolve selected date
    selected_date_str = request.GET.get('date', working_days[0].isoformat())
    try:
        selected_date = date_cls.fromisoformat(selected_date_str)
    except (ValueError, TypeError):
        selected_date = working_days[0]
    if selected_date not in working_days:
        selected_date = working_days[0]

    total_daily_capacity = len(SlotBooking.TIME_SLOTS) * SlotBooking.SLOT_CAPACITY  # 140

    # Date strip data
    days_data = []
    for wd in working_days:
        total_booked = SlotBooking.objects.filter(
            date=wd, status__in=['booked', 'completed']
        ).count()
        pct = total_booked / total_daily_capacity if total_daily_capacity else 0
        if pct == 0:
            crowd_label, crowd_cls = 'Open', 'crowd-none'
        elif pct < 0.3:
            crowd_label, crowd_cls = 'Low', 'crowd-low'
        elif pct < 0.6:
            crowd_label, crowd_cls = 'Medium', 'crowd-medium'
        else:
            crowd_label, crowd_cls = 'High', 'crowd-high'
        days_data.append({
            'date': wd,
            'day_name': wd.strftime('%a'),
            'day_num': wd.strftime('%d'),
            'month': wd.strftime('%b'),
            'total_booked': total_booked,
            'pct': round(pct * 100),
            'crowd_label': crowd_label,
            'crowd_cls': crowd_cls,
            'is_today': wd == today,
            'is_selected': wd == selected_date,
        })

    # User's active booking for selected date
    user_booking = SlotBooking.objects.filter(
        user=request.user, date=selected_date, status__in=['booked', 'completed']
    ).first()

    # Time slot data for selected date
    slot_data = []
    for slot_key, slot_name in SlotBooking.TIME_SLOTS:
        slot_hour = int(slot_key.split(':')[0])
        is_past = (selected_date == today and now.hour > slot_hour) or (selected_date < today)
        is_active = selected_date == today and now.hour == slot_hour

        booked_count = SlotBooking.objects.filter(
            date=selected_date, time_slot=slot_key, status__in=['booked', 'completed']
        ).count()
        remaining = SlotBooking.SLOT_CAPACITY - booked_count
        prefix = SlotBooking.SLOT_PREFIXES.get(slot_key, 'X')

        is_my_slot = user_booking and user_booking.time_slot == slot_key
        can_book = (not (booked_count >= SlotBooking.SLOT_CAPACITY)
                    and not is_past
                    and user_booking is None)

        slot_data.append({
            'key': slot_key,
            'name': slot_name,
            'hour': slot_hour,
            'booked': booked_count,
            'capacity': SlotBooking.SLOT_CAPACITY,
            'remaining': max(0, remaining),
            'is_full': booked_count >= SlotBooking.SLOT_CAPACITY,
            'is_past': is_past,
            'is_active': is_active,
            'crowd_pct': round(booked_count / SlotBooking.SLOT_CAPACITY * 100),
            'token_start': f"{prefix}-001",
            'token_end': f"{prefix}-{booked_count:03d}" if booked_count else f"{prefix}-000",
            'avg_wait': booked_count * 3,
            'is_my_slot': is_my_slot,
            'my_token': user_booking.token_number if is_my_slot else None,
            'can_book': can_book,
        })

    # Live queue status (today only)
    queue_status = None
    if selected_date == today:
        active_slot_key = None
        for slot_key, _ in SlotBooking.TIME_SLOTS:
            if now.hour == int(slot_key.split(':')[0]):
                active_slot_key = slot_key
                break

        if active_slot_key:
            slot_hour = int(active_slot_key.split(':')[0])
            minutes_elapsed = (now.hour - slot_hour) * 60 + now.minute
            current_position = min(max(1, minutes_elapsed // 3), SlotBooking.SLOT_CAPACITY)
            prefix = SlotBooking.SLOT_PREFIXES.get(active_slot_key, 'X')
            current_token = f"{prefix}-{current_position:03d}"

            total_in_slot = SlotBooking.objects.filter(
                date=today, time_slot=active_slot_key, status__in=['booked', 'completed']
            ).count()
            today_total = SlotBooking.objects.filter(date=today, status__in=['booked', 'completed']).count()
            pct = round(today_total / total_daily_capacity * 100) if total_daily_capacity else 0
            crowd = ('Low', 'crowd-low') if pct < 30 else (('Medium', 'crowd-medium') if pct < 60 else ('High', 'crowd-high'))

            tokens_ahead, est_wait, my_token = 0, 0, None
            if user_booking and user_booking.time_slot == active_slot_key:
                my_token = user_booking.token_number
                try:
                    my_num = int(my_token.split('-')[1])
                    tokens_ahead = max(0, my_num - current_position)
                    est_wait = tokens_ahead * 3
                except (IndexError, ValueError):
                    pass

            queue_status = {
                'current_token': current_token,
                'slot_name': dict(SlotBooking.TIME_SLOTS).get(active_slot_key, active_slot_key),
                'tokens_ahead': tokens_ahead,
                'est_wait': est_wait,
                'crowd_label': crowd[0],
                'crowd_cls': crowd[1],
                'total_in_slot': total_in_slot,
                'pct': pct,
                'my_token': my_token,
            }

    # AI recommendation from past 30 days
    thirty_ago = today - timedelta(days=30)

    # Best time slot
    slot_counts = {}
    for slot_key, _ in SlotBooking.TIME_SLOTS:
        slot_counts[slot_key] = SlotBooking.objects.filter(
            date__gte=thirty_ago, time_slot=slot_key, status__in=['booked', 'completed']
        ).count()

    # Day-of-week counts
    dow_counts = defaultdict(int)
    for b in SlotBooking.objects.filter(date__gte=thirty_ago, status__in=['booked', 'completed']).values('date'):
        dow_counts[b['date'].weekday()] += 1

    slot_labels = dict(SlotBooking.TIME_SLOTS)
    best_slot_key = min(slot_counts, key=slot_counts.get) if slot_counts else '12:00'
    worst_slot_key = max(slot_counts, key=slot_counts.get) if slot_counts else '09:00'
    dow_names = {0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 4: 'Friday'}
    best_day = dow_names.get(min(dow_counts, key=dow_counts.get), 'Wednesday') if dow_counts else 'Wednesday'
    worst_day = dow_names.get(max(dow_counts, key=dow_counts.get), 'Monday') if dow_counts else 'Monday'

    ai_rec = {
        'best_slot': slot_labels.get(best_slot_key, best_slot_key),
        'worst_slot': slot_labels.get(worst_slot_key, worst_slot_key),
        'best_day': best_day,
        'worst_day': worst_day,
        'has_data': any(v > 0 for v in slot_counts.values()),
    }

    return render(request, 'certificates/slot_booking.html', {
        'days_data': days_data,
        'selected_date': selected_date,
        'slot_data': slot_data,
        'queue_status': queue_status,
        'ai_rec': ai_rec,
        'user_booking': user_booking,
        'today': today,
        'capacity': SlotBooking.SLOT_CAPACITY,
    })


@login_required
def book_slot_view(request):
    if request.method != 'POST':
        return redirect('slot_booking')

    from datetime import date as date_cls

    date_str = request.POST.get('date', '')
    time_slot = request.POST.get('time_slot', '')
    today = date_cls.today()
    now = timezone.localtime(timezone.now())

    try:
        booking_date = date_cls.fromisoformat(date_str)
    except (ValueError, TypeError):
        messages.error(request, 'Invalid date.')
        return redirect('slot_booking')

    if booking_date < today:
        messages.error(request, 'Cannot book a past date.')
        return redirect(f'/book-slot/?date={date_str}')

    if booking_date.weekday() >= 5:
        messages.error(request, 'Bookings only available Monday to Friday.')
        return redirect(f'/book-slot/?date={date_str}')

    valid_slots = dict(SlotBooking.TIME_SLOTS)
    if time_slot not in valid_slots:
        messages.error(request, 'Invalid time slot.')
        return redirect(f'/book-slot/?date={date_str}')

    slot_hour = int(time_slot.split(':')[0])
    if booking_date == today and now.hour >= slot_hour + 1:
        messages.error(request, 'This time slot has already passed for today.')
        return redirect(f'/book-slot/?date={date_str}')

    existing = SlotBooking.objects.filter(
        user=request.user, date=booking_date, status__in=['booked', 'completed']
    ).first()
    if existing:
        messages.warning(request, f'You already have token {existing.token_number} for this date.')
        return redirect(f'/book-slot/?date={date_str}')

    booked_count = SlotBooking.objects.filter(
        date=booking_date, time_slot=time_slot, status__in=['booked', 'completed']
    ).count()
    if booked_count >= SlotBooking.SLOT_CAPACITY:
        messages.error(request, 'This slot is full. Please select another slot.')
        return redirect(f'/book-slot/?date={date_str}')

    prefix = SlotBooking.SLOT_PREFIXES.get(time_slot, 'X')
    token_number = f"{prefix}-{(booked_count + 1):03d}"

    SlotBooking.objects.create(
        user=request.user,
        date=booking_date,
        time_slot=time_slot,
        token_number=token_number,
        status='booked',
    )

    Notification.objects.create(
        user=request.user,
        title='Slot Booked!',
        message=f'Token {token_number} for {booking_date.strftime("%d %b %Y")} at {valid_slots[time_slot]}.',
        type='success',
    )

    messages.success(request, f'Booked! Your token is {token_number} for {valid_slots[time_slot]} on {booking_date.strftime("%d %b %Y")}.')
    return redirect(f'/book-slot/?date={date_str}')


@login_required
def cancel_slot_view(request, booking_id):
    from datetime import date as date_cls
    booking = get_object_or_404(SlotBooking, id=booking_id, user=request.user)
    date_str = booking.date.isoformat()
    if booking.date < date_cls.today():
        messages.error(request, 'Cannot cancel a past booking.')
    elif booking.status == 'cancelled':
        messages.warning(request, 'Booking is already cancelled.')
    else:
        booking.status = 'cancelled'
        booking.save()
        messages.success(request, f'Booking {booking.token_number} cancelled.')
    return redirect(f'/book-slot/?date={date_str}')


def queue_status_api(request):
    from datetime import date as date_cls
    today = date_cls.today()
    now = timezone.localtime(timezone.now())

    active_slot_key = None
    for slot_key, _ in SlotBooking.TIME_SLOTS:
        if now.hour == int(slot_key.split(':')[0]):
            active_slot_key = slot_key
            break

    if not active_slot_key:
        return JsonResponse({'active': False, 'message': 'No active slot right now'})

    slot_hour = int(active_slot_key.split(':')[0])
    minutes_elapsed = (now.hour - slot_hour) * 60 + now.minute
    current_position = min(max(1, minutes_elapsed // 3), SlotBooking.SLOT_CAPACITY)
    prefix = SlotBooking.SLOT_PREFIXES.get(active_slot_key, 'X')

    total_in_slot = SlotBooking.objects.filter(
        date=today, time_slot=active_slot_key, status__in=['booked', 'completed']
    ).count()
    today_total = SlotBooking.objects.filter(date=today, status__in=['booked', 'completed']).count()
    total_capacity = len(SlotBooking.TIME_SLOTS) * SlotBooking.SLOT_CAPACITY
    pct = round(today_total / total_capacity * 100) if total_capacity else 0
    crowd = 'Low' if pct < 30 else ('Medium' if pct < 60 else 'High')

    return JsonResponse({
        'active': True,
        'current_token': f"{prefix}-{current_position:03d}",
        'total_in_slot': total_in_slot,
        'crowd': crowd,
        'crowd_pct': pct,
        'slot_name': dict(SlotBooking.TIME_SLOTS).get(active_slot_key, ''),
    })
