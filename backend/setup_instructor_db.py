#!/usr/bin/env python
"""
Setup script to initialize the instructor database and create test accounts.
Run this after setting up your Django environment.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kumpas_api.settings')
django.setup()

from django.contrib.auth.models import User
from signtext.models import UserProfile, LearningModule, Announcement, UserLearningState

def create_instructor_account(email, password, full_name, security_pin='1234'):
    """Create an instructor account."""
    try:
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=full_name.split()[0] if full_name else "Instructor",
            last_name=" ".join(full_name.split()[1:]) if len(full_name.split()) > 1 else "",
        )
        
        # Create user profile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'full_name': full_name or "Instructor",
                'role': 'instructor',
                'year_level': 'instructor',
                'security_pin': security_pin
            }
        )
        
        # Create learning state for instructor
        UserLearningState.objects.get_or_create(
            user=user,
            defaults={'state': {}}
        )
        
        if created:
            print(f"✓ Created instructor: {email} ({full_name})")
            print(f"  - Security PIN: {security_pin}")
        else:
            print(f"✓ Instructor already exists: {email}")
        
        return user
    except Exception as e:
        print(f"✗ Error creating instructor: {str(e)}")
        return None


def create_admin_account(email, password, full_name):
    """Create an admin account (only via setup script)."""
    try:
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=full_name.split()[0] if full_name else "Admin",
            last_name=" ".join(full_name.split()[1:]) if len(full_name.split()) > 1 else "",
        )

        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'full_name': full_name or "Admin",
                'role': 'admin',
                'year_level': 'admin',
                'security_pin': ''
            }
        )

        UserLearningState.objects.get_or_create(
            user=user,
            defaults={'state': {}}
        )

        if created:
            print(f"✓ Created admin: {email} ({full_name})")
        else:
            print(f"✓ Admin already exists: {email}")

        return user
    except Exception as e:
        print(f"✗ Error creating admin: {str(e)}")
        return None

def create_student_account(email, password, full_name, year_level):
    """Create a student account."""
    try:
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=full_name.split()[0] if full_name else "Student",
            last_name=" ".join(full_name.split()[1:]) if len(full_name.split()) > 1 else "",
        )
        
        # Create user profile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'full_name': full_name or "Student",
                'role': 'student',
                'year_level': str(year_level)
            }
        )
        
        # Create learning state for student
        UserLearningState.objects.get_or_create(
            user=user,
            defaults={'state': {
                'points': 0,
                'streak': 0,
                'accuracy': 0,
                'moduleProgress': {}
            }}
        )
        
        if created:
            print(f"✓ Created student: {email} ({full_name}) - Year {year_level}")
        else:
            print(f"✓ Student already exists: {email}")
        
        return user
    except Exception as e:
        print(f"✗ Error creating student: {str(e)}")
        return None

def verify_database_setup():
    """Verify that the database is properly set up."""
    print("\n" + "="*60)
    print("DATABASE SETUP VERIFICATION")
    print("="*60)
    
    # Check tables
    print("\n📊 Database Tables:")
    print(f"  • Users: {User.objects.count()}")
    print(f"  • User Profiles: {UserProfile.objects.count()}")
    print(f"  • Learning Modules: {LearningModule.objects.count()}")
    print(f"  • Announcements: {Announcement.objects.count()}")
    print(f"  • Learning States: {UserLearningState.objects.count()}")
    
    # Check for instructor accounts
    instructors = UserProfile.objects.filter(role='instructor')
    print(f"\n👨‍🏫 Instructor Accounts ({instructors.count()}):")
    for profile in instructors:
        print(f"  • {profile.full_name} ({profile.user.email})")
    
    # Check for student accounts
    students = UserProfile.objects.filter(role='student')
    print(f"\n👨‍🎓 Student Accounts ({students.count()}):")
    for profile in students[:10]:  # Show first 10
        print(f"  • {profile.full_name} ({profile.user.email}) - Year {profile.year_level}")
    if students.count() > 10:
        print(f"  ... and {students.count() - 10} more")
    
    # Check for modules
    modules = LearningModule.objects.all()
    print(f"\n📚 Learning Modules ({modules.count()}):")
    for module in modules[:5]:  # Show first 5
        print(f"  • {module.title} (Year {module.year_level}) - Status: {module.status}")
    if modules.count() > 5:
        print(f"  ... and {modules.count() - 5} more")
    
    # Check for announcements
    announcements = Announcement.objects.all()
    print(f"\n📢 Announcements ({announcements.count()}):")
    for announcement in announcements[:3]:  # Show first 3
        print(f"  • {announcement.title}")
    if announcements.count() > 3:
        print(f"  ... and {announcements.count() - 3} more")

def main():
    print("\n" + "="*60)
    print("KUMPAS INSTRUCTOR DATABASE SETUP")
    print("="*60)
    
    # Run migrations first
    print("\n1️⃣  Running Django migrations...")
    os.system('python manage.py migrate --run-syncdb')
    print("✓ Migrations applied")
    
    # Create test accounts
    print("\n2️⃣  Creating test accounts...")
    
    # Create default instructor if doesn't exist
    instructor_profile = UserProfile.objects.filter(user__email='maria@ccnc.edu.ph', role='instructor').first()
    if not instructor_profile:
        create_instructor_account('maria@ccnc.edu.ph', 'instructor123', 'Maria Santos', '1234')
    else:
        # Update existing instructor's PIN if not set
        if not instructor_profile.security_pin:
            instructor_profile.security_pin = '1234'
            instructor_profile.save()
            print(f"✓ Updated instructor security PIN: maria@ccnc.edu.ph")
        else:
            print("✓ Default instructor already exists")
    
    # Create some test students
    test_students = [
        ('juan@student.com', 'student123', 'Juan Dela Cruz', '1'),
        ('ana@student.com', 'student123', 'Ana Martinez', '2'),
        ('carlos@student.com', 'student123', 'Carlos Reyes', '3'),
    ]
    
    for email, pwd, name, year in test_students:
        if not User.objects.filter(email=email).exists():
            create_student_account(email, pwd, name, year)
        else:
            print(f"✓ Student already exists: {email}")

    # Ensure a default admin account exists (do not allow admin registration via UI)
    admin_email = 'admin1@kumpas.local'
    admin_profile = UserProfile.objects.filter(user__email=admin_email, role='admin').first()
    if not admin_profile and not User.objects.filter(email=admin_email).exists():
        create_admin_account(admin_email, 'admin123', 'Admin One')
    else:
        print(f"✓ Admin already exists: {admin_email}")
    
    # Verify setup
    verify_database_setup()
    
    print("\n" + "="*60)
    print("✅ DATABASE SETUP COMPLETE!")
    print("="*60)
    print("\n💡 Next steps:")
    print("  1. Start the Django server:")
    print("     python manage.py runserver 127.0.0.1:8000")
    print("  2. Navigate to: http://localhost:3000/login.html")
    print("  3. Login with instructor account:")
    print("     Email: maria@ccnc.edu.ph")
    print("     Password: instructor123")
    print("     Role: Instructor")
    print("     Security PIN: 1234")
    print("  4. After login, you'll be redirected to instructor-dashboard.html")
    print("\n" + "="*60 + "\n")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        sys.exit(1)
