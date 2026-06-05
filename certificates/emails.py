"""
certificates/emails.py
Sends approval / rejection emails to students.
Uses the same EmailMultiAlternatives path as the working OTP emails.
"""

import re
import traceback
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


def _build_html(status, full_name, cert_type, short_id, mode, note, remarks, app_url):
    support = getattr(settings, 'EMAIL_HOST_USER', 'tatkalservice07@gmail.com')

    if status == 'approved':
        top_color  = '#1a7f37'
        badge_bg   = '#d1fae5'
        badge_fg   = '#065f46'
        badge_txt  = '✅  Application Approved'
        heading    = f'Your {cert_type} certificate is approved!'
        body       = (f'Your <strong>{cert_type}</strong> application has been '
                      f'<strong>approved</strong> and your certificate is ready to download.')
        btn_txt    = 'Download Your Certificate →'
        btn_color  = '#1a7f37'
    else:
        top_color  = '#b91c1c'
        badge_bg   = '#fee2e2'
        badge_fg   = '#991b1b'
        badge_txt  = '❌  Application Rejected'
        heading    = f'Your {cert_type} application was not approved'
        body       = (f'Your <strong>{cert_type}</strong> application has been '
                      f'<strong>rejected</strong>. Please review the reason and contact '
                      f'the university office or reapply after addressing the issue.')
        btn_txt    = 'View Application Details →'
        btn_color  = '#0a2463'

    extra = ''
    if note:
        extra += f'<p style="margin:8px 0 0"><strong>Note:</strong> {note}</p>'
    if remarks:
        extra += f'<p style="margin:8px 0 0"><strong>Remarks:</strong> {remarks}</p>'
    extra_block = (
        f'<div style="background:#fffde7;border-left:4px solid #f5c518;'
        f'border-radius:6px;padding:12px 16px;margin:16px 0;font-size:14px;color:#5d4037">'
        f'{extra}</div>'
    ) if extra else ''

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{heading}</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;
             font-family:'Segoe UI',Arial,Helvetica,sans-serif;color:#1e293b">
<div style="max-width:580px;margin:36px auto;background:#fff;border-radius:16px;
            overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.10)">

  <!-- Header -->
  <div style="background:{top_color};padding:32px 36px;text-align:center">
    <div style="font-size:34px;margin-bottom:8px">🎓</div>
    <h1 style="color:#fff;margin:0;font-size:20px;font-weight:800">Kakatiya University</h1>
    <p style="color:rgba(255,255,255,.80);margin:6px 0 0;font-size:13px">
      Smart Tatkal Certificate Management System
    </p>
  </div>

  <!-- Badge -->
  <div style="padding:28px 36px 0;text-align:center">
    <span style="display:inline-block;padding:8px 24px;border-radius:999px;
                 background:{badge_bg};color:{badge_fg};font-size:14px;font-weight:700">
      {badge_txt}
    </span>
  </div>

  <!-- Body -->
  <div style="padding:24px 36px 32px">
    <p style="margin:0 0 10px;font-size:15px">Dear <strong>{full_name}</strong>,</p>
    <p style="margin:0 0 20px;font-size:14px;line-height:1.75;color:#374151">{body}</p>

    <!-- Details card -->
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;
                padding:18px 22px;margin-bottom:20px">
      <p style="margin:0 0 10px;font-size:11px;font-weight:700;letter-spacing:.08em;
                text-transform:uppercase;color:#94a3b8">Application Details</p>
      <table style="width:100%;border-collapse:collapse">
        <tr>
          <td style="padding:7px 0;border-bottom:1px solid #f1f5f9;
                     color:#64748b;font-size:13px;width:40%">Application ID</td>
          <td style="padding:7px 0;border-bottom:1px solid #f1f5f9;
                     font-size:13px;font-weight:600;color:#0a2463">#{short_id}</td>
        </tr>
        <tr>
          <td style="padding:7px 0;border-bottom:1px solid #f1f5f9;
                     color:#64748b;font-size:13px">Certificate Type</td>
          <td style="padding:7px 0;border-bottom:1px solid #f1f5f9;
                     font-size:13px;font-weight:500">{cert_type}</td>
        </tr>
        <tr>
          <td style="padding:7px 0;color:#64748b;font-size:13px">Mode</td>
          <td style="padding:7px 0;font-size:13px;font-weight:500">{mode}</td>
        </tr>
      </table>
    </div>

    {extra_block}

    <!-- Button -->
    <div style="text-align:center;margin-top:24px">
      <a href="{app_url}"
         style="display:inline-block;background:{btn_color};color:#fff;
                padding:14px 32px;border-radius:10px;text-decoration:none;
                font-size:14px;font-weight:700">{btn_txt}</a>
    </div>
  </div>

  <!-- Footer -->
  <div style="background:#f8fafc;border-top:1px solid #e2e8f0;
              padding:18px 36px;text-align:center">
    <p style="margin:0;font-size:12px;color:#94a3b8;line-height:1.6">
      Automated notification from <strong>Kakatiya University Tatkal CMS</strong>.<br/>
      Do not reply · Support:
      <a href="mailto:{support}" style="color:#0a2463;text-decoration:none">{support}</a>
    </p>
  </div>

</div>
</body>
</html>"""


def send_status_email(application, new_status, note='', staff_remarks=''):
    """
    Send approval or rejection email to the student.
    Called from update_status_view after the DB is saved.
    Never raises — all errors are printed to the runserver console.
    """

    # Only email for these two actions
    if new_status not in ('approved', 'rejected'):
        print(f"[Email] '{new_status}' — no email sent (only approved/rejected trigger emails).")
        return

    student_user  = application.student.user
    student_email = (student_user.email or '').strip()
    short_id      = application.get_short_id()
    cert_type     = application.get_certificate_type_display()
    full_name     = student_user.get_full_name() or student_user.username
    mode          = '⚡ Tatkal' if application.is_tatkal else 'Normal'
    app_url       = f"http://localhost:8000/applications/{application.application_id}/"
    from_email    = getattr(settings, 'DEFAULT_FROM_EMAIL', 'tatkalservice07@gmail.com')

    if not student_email:
        print(f"[Email] ⚠️  No email address for student '{student_user.username}' — skipping.")
        return

    subject = (
        f"✅ Your {cert_type} Certificate is Approved – Tatkal CMS"
        if new_status == 'approved' else
        f"❌ Your {cert_type} Application was Rejected – Tatkal CMS"
    )

    html  = _build_html(new_status, full_name, cert_type, short_id,
                        mode, note, staff_remarks, app_url)
    plain = re.sub(r'<[^>]+>', ' ', html)
    plain = re.sub(r'\s+', ' ', plain).strip()

    print(f"[Email] Sending '{new_status}' notification → {student_email}")

    try:
        msg = EmailMultiAlternatives(
            subject    = subject,
            body       = plain,
            from_email = from_email,
            to         = [student_email],
        )
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=False)
        print(f"[Email] ✅ Sent '{new_status}' email to {student_email} for #{short_id}")

    except Exception:
        print(f"[Email] ❌ Failed to send email to {student_email}:")
        print(traceback.format_exc())


def send_test_email(to_email):
    """Test SMTP config. Returns (success: bool, message: str)."""
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'tatkalservice07@gmail.com')
    html = f"""<div style="font-family:Arial;max-width:480px;margin:40px auto;
                background:#fff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden">
      <div style="background:#0a2463;padding:20px;text-align:center">
        <h2 style="color:#f5c518;margin:0">🎓 Tatkal CMS — Email Test</h2>
      </div>
      <div style="padding:24px">
        <p style="font-size:15px">✅ <strong>Gmail SMTP is working correctly!</strong></p>
        <p style="color:#64748b;font-size:13px">
          Approval and rejection emails will be delivered to students automatically.
        </p>
      </div>
    </div>"""
    try:
        msg = EmailMultiAlternatives(
            "✅ Tatkal CMS – Email Test OK",
            "Email is working correctly.",
            from_email,
            [to_email],
        )
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=False)
        return True, f"Test email sent to {to_email} successfully."
    except Exception as e:
        return False, str(e)
