"""
Run this to confirm email works:
  python test_email_now.py [recipient@example.com]
"""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tatkal_cms.settings')
django.setup()

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

to_email = sys.argv[1] if len(sys.argv) > 1 else settings.EMAIL_HOST_USER

print("Backend :", settings.EMAIL_BACKEND)
print("Host    :", getattr(settings, 'EMAIL_HOST', 'N/A'))
print("User    :", settings.EMAIL_HOST_USER)
print("From    :", settings.DEFAULT_FROM_EMAIL)
print("To      :", to_email)
print()
print(f"Sending test email to {to_email} ...")

try:
    msg = EmailMultiAlternatives(
        subject    = 'TEST - Tatkal CMS Email Working',
        body       = 'Email is working. Approvals and rejections will now send emails.',
        from_email = settings.DEFAULT_FROM_EMAIL,
        to         = [to_email],
    )
    msg.send(fail_silently=False)
    print(f"SUCCESS - Check inbox of {to_email}")
except Exception as e:
    print("FAILED:", e)
