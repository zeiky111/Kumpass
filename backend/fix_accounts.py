#!/usr/bin/env python
"""
Fix admin and teacher accounts.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kumpas_api.settings')
django.setup()

from django.contrib.auth.models import User
from signtext.models import UserProfile, UserLearningState


def fix_admin_account():
    """Fix/reset admin account."""
    print("\n" + "="*60)
    print("FIXING ADMIN ACCOUNT")
    print("="*60)
    
    admin_username = 'admin1'
    admin_email = 'admin1@kumpas'
    admin_password = 'admin123'
    
    try:
        # Try to get existing admin
        admin_user = User.objects.filter(username=admin_username).first()
        
        if admin_user:
            # Reset password
            admin_user.email = admin_email
            admin_user.set_password(admin_password)
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.is_active = True
            admin_user.save()
            print(f"✓ Reset admin account:")
            print(f"  - Username: {admin_username}")
            print(f"  - Email: {admin_email}")
            print(f"  - Password: {admin_password}")
            print(f"  - Active: True")
            
            # Ensure profile exists
            profile, created = UserProfile.objects.get_or_create(
                user=admin_user,
                defaults={
                    'full_name': 'System Admin',
                    'role': 'admin',
                    'year_level': 'admin'
                }
            )
            if created:
                print(f"✓ Created admin profile")
        else:
            # Create new admin
            admin_user = User.objects.create_superuser(
                username=admin_username,
                email=admin_email,
                password=admin_password
            )
            UserProfile.objects.get_or_create(
                user=admin_user,
                defaults={
                    'full_name': 'System Admin',
                    'role': 'admin',
                    'year_level': 'admin'
                }
            )
            print(f"✓ Created new admin account:")
            print(f"  - Username: {admin_username}")
            print(f"  - Email: {admin_email}")
            print(f"  - Password: {admin_password}")
            
    except Exception as e:
        print(f"✗ Error fixing admin: {str(e)}")


def convert_to_teacher(email):
    """Convert irish@gmail.com to teacher account."""
    print("\n" + "="*60)
    print(f"CONVERTING {email} TO TEACHER")
    print("="*60)
    
    try:
        # Find user
        user = User.objects.filter(email=email).first()
        
        if not user:
            print(f"✗ User not found: {email}")
            return
        
        # Update user to be staff
        user.is_staff = True
        user.save()
        
        # Get or create profile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'full_name': user.first_name or 'Teacher',
                'role': 'instructor',
                'year_level': 'instructor',
                'security_pin': '1234'
            }
        )
        
        # Update existing profile
        if not created:
            profile.role = 'instructor'
            profile.year_level = 'instructor'
            if not profile.security_pin:
                profile.security_pin = '1234'
            profile.save()
        
        # Ensure learning state exists
        UserLearningState.objects.get_or_create(
            user=user,
            defaults={'state': {}}
        )
        
        print(f"✓ Converted {email} to teacher/instructor:")
        print(f"  - Role: instructor")
        print(f"  - Is Staff: True")
        print(f"  - Security PIN: 1234")
        print(f"  - Profile: {profile.full_name}")
        
    except Exception as e:
        print(f"✗ Error converting user: {str(e)}")


if __name__ == '__main__':
    # Fix admin account
    fix_admin_account()
    
    # Convert irish@gmail.com to teacher
    convert_to_teacher('irish@gmail.com')
    
    print("\n" + "="*60)
    print("ACCOUNT FIX COMPLETE")
    print("="*60)
