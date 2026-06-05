"""
Run this FIRST to confirm email works:
  python test_email_now.py
"""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tatkal_cms.settings')
django.setup()

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

print("Backend :", settings.EMAIL_BACKEND)
print("Host    :", settings.EMAIL_HOST)
print("User    :", settings.EMAIL_HOST_USER)
print("Pass    :", settings.EMAIL_HOST_PASSWORD[:4] + '****')
print("From    :", settings.DEFAULT_FROM_EMAIL)
print()
print("Sending test email to tatkalservice07@gmail.com ...")

try:
    msg = EmailMultiAlternatives(
        subject    = 'TEST - Tatkal CMS Email Working',
        body       = 'Email is working. Approvals and rejections will now send emails.',
        from_email = 'tatkalservice07@gmail.com',
        to         = ['tatkalservice07@gmail.com'],
    )
    msg.send(fail_silently=False)
    print("SUCCESS - Check inbox of tatkalservice07@gmail.com")
except Exception as e:
    print("FAILED:", e)
