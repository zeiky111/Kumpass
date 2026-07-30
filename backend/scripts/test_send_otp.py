import os
import django
import sys
from datetime import datetime

# Ensure backend package is importable (add project backend dir to sys.path)
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_BACKEND_DIR = os.path.abspath(os.path.join(THIS_DIR, '..'))
if PROJECT_BACKEND_DIR not in sys.path:
    sys.path.insert(0, PROJECT_BACKEND_DIR)

# Force console backend for this test run
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kumpas_api.settings')
os.environ.setdefault('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')

django.setup()

from django.contrib.auth.models import User
from signtext.views import _create_and_send_otp


def main():
    test_email = os.environ.get('TEST_OTP_EMAIL', 'test.otp@example.com')
    print(f"[test_send_otp] Running at {datetime.now().isoformat()}, using email: {test_email}")

    user, created = User.objects.get_or_create(username=test_email, defaults={
        'email': test_email,
        'first_name': 'OTP',
        'last_name': 'Tester',
    })
    if created:
        user.set_password('TempPass123!')
        user.is_active = False
        user.save()

    try:
        _create_and_send_otp(user, request=None, minutes_valid=15)
        print('[test_send_otp] _create_and_send_otp executed — check console output above for OTP email body')
    except Exception as e:
        print('[test_send_otp] Exception while sending OTP:', e)
        sys.exit(2)


if __name__ == '__main__':
    main()
