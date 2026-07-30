#!/usr/bin/env python
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kumpas_api.settings")
sys.path.insert(0, os.path.dirname(__file__))

import django
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

EMAIL = "irish@gmail.com"
NEW_PASSWORD = "irish16101818"

try:
    user = User.objects.get(email=EMAIL)
    user.set_password(NEW_PASSWORD)
    user.save()
    print(f"Password for {EMAIL} updated successfully.")
except User.DoesNotExist:
    print(f"User with email {EMAIL} not found.")
except Exception as e:
    print("Error:", e)
