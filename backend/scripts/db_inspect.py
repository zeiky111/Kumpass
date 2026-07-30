import os
import django
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kumpas_api.settings')
django.setup()

from django.contrib.auth.models import User
from signtext.models import UserProfile

print('USERS', User.objects.count())
print(list(User.objects.values('id','username','email')[:50]))
print('PROFILES', UserProfile.objects.count())
print(list(UserProfile.objects.values('user_id','full_name','role','active')[:50]))
