#!/usr/bin/env python
"""
Test OTP sending with a real user registration email
"""
import os
import sys
import django

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kumpas_api.settings')
django.setup()

from django.contrib.auth.models import User
from signtext.models import EmailOTP
from signtext.views import _create_and_send_otp
import logging

logging.basicConfig(level=logging.INFO)

# Create a test user with a specific email
test_email = "testuser2026@example.com"
test_username = "testuser2026"

print(f"\n{'='*70}")
print("TESTING OTP SENDING TO USER'S REGISTERED EMAIL")
print(f"{'='*70}\n")

# Delete existing test user if it exists
User.objects.filter(username=test_username).delete()

# Create test user
print(f"Creating user: {test_username}")
print(f"With email: {test_email}\n")

user = User.objects.create_user(
    username=test_username,
    email=test_email,
    password="testpass123"
)

print(f"✅ User created successfully")
print(f"   Username: {user.username}")
print(f"   Email: {user.email}\n")

# Send OTP
print(f"Sending OTP to {user.email}...\n")
result = _create_and_send_otp(user, request=None, minutes_valid=15)

if result.get("ok"):
    print(f"✅ OTP sent successfully to {user.email}!\n")
    
    # Show OTP details
    latest_otp = EmailOTP.objects.filter(user=user).order_by('-created_at').first()
    if latest_otp:
        print(f"   OTP Code: {latest_otp.otp}")
        print(f"   Expires at: {latest_otp.expires_at}")
        print(f"   Created at: {latest_otp.created_at}\n")
else:
    print(f"❌ OTP sending FAILED: {result.get('error')}\n")

print(f"{'='*70}")
print("TEST COMPLETE - Check your email for the OTP code")
print(f"{'='*70}\n")
