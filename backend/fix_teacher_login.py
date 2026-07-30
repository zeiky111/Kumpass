#!/usr/bin/env python
"""
Check and fix irish@gmail.com teacher account login issues.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kumpas_api.settings')
django.setup()

from django.contrib.auth.models import User
from signtext.models import UserProfile


def check_and_fix_teacher():
    """Check and fix teacher account."""
    email = 'irish@gmail.com'
    
    print("\n" + "="*60)
    print(f"CHECKING {email}")
    print("="*60)
    
    try:
        user = User.objects.filter(email=email).first()
        
        if not user:
            print(f"✗ User not found")
            return
        
        print(f"\nUser Details:")
        print(f"  - Username: {user.username}")
        print(f"  - Email: {user.email}")
        print(f"  - Is Active: {user.is_active}")
        print(f"  - Is Staff: {user.is_staff}")
        print(f"  - Is Superuser: {user.is_superuser}")
        
        profile = UserProfile.objects.filter(user=user).first()
        if profile:
            print(f"\nProfile Details:")
            print(f"  - Full Name: {profile.full_name}")
            print(f"  - Role: {profile.role}")
            print(f"  - Active: {profile.active}")
        
        # Fix issues
        print(f"\nApplying fixes...")
        
        # Make sure account is active
        if not user.is_active:
            user.is_active = True
            print(f"  ✓ Activated user account")
        
        # Make sure is_staff is set
        if not user.is_staff:
            user.is_staff = True
            print(f"  ✓ Set is_staff=True")
        
        # Set a password
        new_password = 'teacher123'
        user.set_password(new_password)
        user.save()
        print(f"  ✓ Set password: {new_password}")
        
        # Fix profile
        if profile:
            if profile.active != 0:
                profile.active = 0
                profile.save()
                print(f"  ✓ Set profile active=0")
        
        print(f"\n✅ ACCOUNT READY TO LOGIN:")
        print(f"  - Email: {email}")
        print(f"  - Password: {new_password}")
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    check_and_fix_teacher()
