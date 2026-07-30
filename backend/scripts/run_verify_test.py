import os
import django
import json
import sys

# Ensure the project backend path is on sys.path so imports succeed when
# running this script directly.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kumpas_api.settings')
django.setup()

from django.contrib.auth.models import User
from signtext.models import UserProfile, EmailOTP
from signtext.views import _create_and_send_otp
from django.test import Client

TEST_EMAIL = os.environ.get('TEST_VERIFY_EMAIL', 'verify.test@example.com')
PASSWORD = 'TestPass123!'

# Clean up any existing test user
User.objects.filter(username=TEST_EMAIL).delete()

# Create user and profile
user = User.objects.create_user(username=TEST_EMAIL, email=TEST_EMAIL, password=PASSWORD, first_name='Test', last_name='User')
UserProfile.objects.create(user=user, full_name='Test User', first_name='Test', last_name='User', year_level='1', role='student')
user.is_active = False
user.save(update_fields=['is_active'])

print('[run_verify_test] Created user:', TEST_EMAIL)

# Generate OTP
result = _create_and_send_otp(user, request=None, minutes_valid=15)
print('[run_verify_test] _create_and_send_otp result:', result)

latest = EmailOTP.objects.filter(user=user).order_by('-created_at').first()
if latest:
    print('[run_verify_test] OTP in DB:', latest.otp)
else:
    print('[run_verify_test] No OTP found in DB')

# Use Django test client to POST to verify endpoint
client = Client()
resp = client.post('/api/auth/verify-email/', data={'email': TEST_EMAIL, 'otp': latest.otp}, content_type='application/json')
print('[run_verify_test] verify-email status:', resp.status_code)
try:
    print('[run_verify_test] verify-email response:', json.loads(resp.content.decode()))
except Exception:
    print('[run_verify_test] verify-email raw response:', resp.content.decode())

user.refresh_from_db()
print('[run_verify_test] user.is_active after verify:', user.is_active)

# cleanup
EmailOTP.objects.filter(user=user).delete()
User.objects.filter(username=TEST_EMAIL).delete()
print('[run_verify_test] cleanup done')
