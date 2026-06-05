from django.contrib import admin
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from .models import Application, Certificate, ApplicationStatusHistory


def send_status_mail(application, status):
    student_email = (application.student.user.email or '').strip()
    if not student_email:
        print(f'[Email] No email found for student — skipped.')
        return

    name      = application.student.user.get_full_name() or application.student.user.username
    cert      = application.get_certificate_type_display()
    short_id  = application.get_short_id()
    from_addr = settings.DEFAULT_FROM_EMAIL
    app_url   = f'{settings.BASE_URL}/applications/{application.application_id}/'

    if status == 'approved':
        subject = f'Your {cert} Certificate is Approved - Tatkal CMS'
        color   = '#1a7f37'
        title   = 'Application Approved ✅'
        message = f'Your {cert} application (#{short_id}) has been APPROVED. Your certificate is ready to download.'
        btn     = 'Download Certificate'
    else:
        subject = f'Your {cert} Application was Rejected - Tatkal CMS'
        color   = '#b91c1c'
        title   = 'Application Rejected ❌'
        message = f'Your {cert} application (#{short_id}) has been REJECTED. Please contact the university office.'
        btn     = 'View Application'

    plain = f'Dear {name},\n\n{message}\n\nView: {app_url}\n\n{settings.UNIVERSITY_NAME} Tatkal CMS'

    html = f"""
<div style="font-family:Arial,sans-serif;max-width:540px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0">
  <div style="background:{color};padding:28px 32px;text-align:center">
    <h2 style="color:#fff;margin:0;font-size:1.2rem">{settings.UNIVERSITY_NAME} - Tatkal CMS</h2>
  </div>
  <div style="padding:28px 32px">
    <p style="font-size:1rem;font-weight:700;color:{color}">{title}</p>
    <p style="color:#374151;font-size:14px">Dear <strong>{name}</strong>,</p>
    <p style="color:#374151;font-size:14px;line-height:1.7">{message}</p>
    <div style="background:#f8fafc;border-radius:8px;padding:14px;margin:16px 0;font-size:13px">
      <b>Application ID:</b> #{short_id}<br>
      <b>Certificate:</b> {cert}<br>
      <b>Student:</b> {name}
    </div>
    <a href="{app_url}" style="display:inline-block;background:{color};color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:700">{btn} →</a>
  </div>
  <div style="background:#f8fafc;padding:14px 32px;text-align:center;font-size:12px;color:#94a3b8">
    Sent from {settings.SUPPORT_EMAIL} · {settings.UNIVERSITY_NAME} Tatkal CMS
  </div>
</div>"""

    try:
        msg = EmailMultiAlternatives(subject, plain, from_addr, [student_email])
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=False)
        print(f'[Email] ✅ {status} email sent to {student_email}')
    except Exception as e:
        print(f'[Email] ❌ Failed: {e}')


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display  = ['get_short_id', 'student', 'certificate_type', 'is_tatkal', 'status', 'payment_status', 'created_at']
    list_filter   = ['status', 'is_tatkal', 'certificate_type', 'payment_status']
    search_fields = ['student__user__first_name', 'student__student_id']

    def save_model(self, request, obj, form, change):
        old_status = None
        if change and obj.pk:
            try:
                old_status = Application.objects.get(pk=obj.pk).status
            except Application.DoesNotExist:
                pass

        super().save_model(request, obj, form, change)

        if old_status != obj.status and obj.status in ('approved', 'rejected'):
            print(f'[Email] Status: {old_status} → {obj.status} | Sending email...')
            send_status_mail(obj, obj.status)


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['verification_code', 'application', 'issued_at', 'is_valid']


admin.site.register(ApplicationStatusHistory)
