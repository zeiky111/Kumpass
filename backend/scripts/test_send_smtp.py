import os, django, sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_BACKEND_DIR = os.path.abspath(os.path.join(THIS_DIR, '..'))
if PROJECT_BACKEND_DIR not in sys.path:
    sys.path.insert(0, PROJECT_BACKEND_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kumpas_api.settings')
# Do NOT override EMAIL_BACKEND; use whatever is in .env

django.setup()

from django.core.mail import send_mail
from django.conf import settings

print('Using EMAIL_BACKEND:', settings.EMAIL_BACKEND)
print('EMAIL_HOST_USER:', settings.EMAIL_HOST_USER)

try:
    sent = send_mail(
        'Kumpas SMTP test',
        'This is a test email sent by test_send_smtp.py',
        settings.DEFAULT_FROM_EMAIL,
        [os.environ.get('TEST_SMTP_TO', settings.EMAIL_HOST_USER or 'test@example.com')],
        fail_silently=False,
    )
    print('send_mail returned:', sent)
except Exception as e:
    print('send_mail exception:', repr(e))
    raise
