import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kumpas_api.settings')
import django
from django.test.client import RequestFactory
from signtext.views import request_password_reset
from signtext.models import User

django.setup()

User.objects.filter(username='test-reset@example.com').delete()
User.objects.create_user(username='test-reset@example.com', email='test-reset@example.com', password='TempPass123!')

rf = RequestFactory()
req = rf.post('/api/auth/request-password-reset/', data=json.dumps({'email': 'test-reset@example.com'}), content_type='application/json')
res = request_password_reset(req)
print('status', res.status_code)
print('data', res.data)
