#!/usr/bin/env python
"""
Comprehensive email/OTP diagnosis script.
Run with: python scripts/diagnose_email.py
"""
import os
import sys
import django
import smtplib
from datetime import datetime

# Add backend directory to path so we can import kumpas_api
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kumpas_api.settings')
django.setup()

from django.conf import settings
from django.core.mail import send_mail, get_connection

print("\n" + "="*70)
print("KUMPAS EMAIL CONFIGURATION DIAGNOSTIC")
print("="*70 + "\n")

# 1. Check environment variables
print("1. CHECKING EMAIL ENVIRONMENT VARIABLES:")
print("-" * 70)
print(f"   EMAIL_BACKEND:     {settings.EMAIL_BACKEND}")
print(f"   EMAIL_HOST:        {settings.EMAIL_HOST}")
print(f"   EMAIL_PORT:        {settings.EMAIL_PORT}")
print(f"   EMAIL_HOST_USER:   {settings.EMAIL_HOST_USER}")
print(f"   EMAIL_USE_TLS:     {settings.EMAIL_USE_TLS}")
print(f"   EMAIL_USE_SSL:     {settings.EMAIL_USE_SSL}")
print(f"   DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")

# 2. Validate settings
print("\n2. VALIDATING CONFIGURATION:")
print("-" * 70)
errors = []

if not settings.EMAIL_HOST_USER:
    errors.append("❌ EMAIL_HOST_USER is empty!")
if not settings.EMAIL_HOST_PASSWORD:
    errors.append("❌ EMAIL_HOST_PASSWORD is empty!")
if settings.EMAIL_BACKEND != "django.core.mail.backends.smtp.EmailBackend":
    errors.append("❌ EMAIL_BACKEND is not set to SMTP!")
if settings.EMAIL_HOST != "smtp.gmail.com":
    errors.append("⚠️  EMAIL_HOST should be 'smtp.gmail.com' for Gmail")

if errors:
    for err in errors:
        print(f"   {err}")
else:
    print("   ✅ All settings look correct")

# 3. Test SMTP connection
print("\n3. TESTING SMTP CONNECTION:")
print("-" * 70)
try:
    connection = get_connection()
    connection.open()
    print("   ✅ Successfully connected to SMTP server!")
    connection.close()
except smtplib.SMTPAuthenticationError as e:
    print(f"   ❌ AUTHENTICATION FAILED: {e}")
    print(f"   - Check your EMAIL_HOST_USER and EMAIL_HOST_PASSWORD")
    print(f"   - For Gmail: Use an App Password, not your main password")
    print(f"   - Ensure 2FA is enabled on your Gmail account")
except smtplib.SMTPException as e:
    print(f"   ❌ SMTP ERROR: {e}")
except Exception as e:
    print(f"   ❌ CONNECTION FAILED: {e}")

# 4. Test email sending
print("\n4. TESTING EMAIL SENDING:")
print("-" * 70)
try:
    # Try sending a test email
    result = send_mail(
        subject="Kumpas Email Test",
        message=f"Test email sent at {datetime.now().isoformat()}\nIf you received this, email is working!",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.EMAIL_HOST_USER],  # Send to yourself for testing
        fail_silently=False
    )
    print(f"   ✅ Email sent successfully!")
    print(f"   Check your inbox at: {settings.EMAIL_HOST_USER}")
except Exception as e:
    print(f"   ❌ FAILED TO SEND EMAIL: {e}")
    import traceback
    traceback.print_exc()

# 5. Test OTP sending
print("\n5. TESTING OTP FUNCTIONALITY:")
print("-" * 70)
try:
    from django.contrib.auth.models import User
    from signtext.views import _create_and_send_otp
    
    # Find a test user or create one
    test_user = User.objects.filter(username="testuser").first()
    if not test_user:
        print("   ⚠️  No 'testuser' found. Creating test user...")
        test_user, created = User.objects.get_or_create(
            username="testuser",
            defaults={"email": settings.EMAIL_HOST_USER}
        )
        if created:
            print(f"   ✅ Created test user: {test_user.username}")
    
    print(f"   Sending OTP to: {test_user.email}")
    result = _create_and_send_otp(test_user, request=None, minutes_valid=15)
    
    if result.get("ok"):
        print(f"   ✅ OTP sent successfully!")
        # Show OTP details
        from signtext.models import EmailOTP
        latest_otp = EmailOTP.objects.filter(user=test_user).order_by('-created_at').first()
        if latest_otp:
            print(f"   OTP Code: {latest_otp.otp}")
            print(f"   Expires at: {latest_otp.expires_at}")
    else:
        print(f"   ❌ OTP sending failed: {result.get('error')}")
        
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("DIAGNOSTIC COMPLETE")
print("="*70 + "\n")
