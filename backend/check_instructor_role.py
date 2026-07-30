#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kumpas_api.settings")
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.contrib.auth.models import User
from signtext.models import UserProfile

print("\n=== INSTRUCTOR/ADMIN USERS ===\n")
profiles = UserProfile.objects.select_related('user').filter(role__in=['instructor', 'admin'])

if not profiles.exists():
    print("❌ NO INSTRUCTOR OR ADMIN USERS FOUND\n")
else:
    for profile in profiles:
        status = "✅ ACTIVE" if profile.active == 0 else "❌ INACTIVE"
        print(f"Username: {profile.user.username}")
        print(f"Email: {profile.user.email}")
        print(f"Role: {profile.role}")
        print(f"Status: {status}")
        print()

print("=== ALL USERS ===\n")
for user in User.objects.all():
    profile = getattr(user, 'profile', None)
    role = profile.role if profile else "NO PROFILE"
    print(f"- {user.username} ({user.email}) → {role}")
