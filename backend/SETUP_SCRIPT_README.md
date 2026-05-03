#!/usr/bin/env python
"""
KUMPAS Instructor Database Setup Script

This script initializes the instructor-related database tables, applies migrations,
and creates test accounts for development and testing.

Usage:
    python setup_instructor_db.py

What it does:
    1. Applies Django migrations to create/update tables
    2. Creates a default instructor account (Maria Santos)
    3. Creates 3 test student accounts
    4. Seeds learning modules (8 pre-loaded lessons)
    5. Seeds announcements (3 sample announcements)
    6. Verifies the database setup
    7. Displays account credentials

Prerequisites:
    - Django installed and configured
    - SQLite database file exists at backend/db.sqlite3
    - Python 3.7+

Database Tables Created/Used:
    - auth_user (Django built-in)
    - signtext_userprofile (Custom User profiles)
    - signtext_userlearningstate (Student learning progress)
    - signtext_learningmodule (FSL lessons/modules)
    - signtext_announcement (Instructor announcements)

Test Credentials Created:
    Instructor:
        Email: maria@ccnc.edu.ph
        Password: instructor123
        Security PIN: 1234

    Students:
        juan@student.com / student123 (Year 1)
        ana@student.com / student123 (Year 2)
        carlos@student.com / student123 (Year 3)

Pre-loaded Data:
    - 8 Learning Modules (Lessons 1-8 across years 1-4)
    - 3 Sample Announcements
    - Instructor user profile
    - Student user profiles

Running the Script:
    1. Navigate to backend folder
    2. Run: python setup_instructor_db.py
    3. The script will:
        - Run migrations
        - Create/update accounts
        - Verify database integrity
        - Display setup summary

Output:
    The script will output:
    - Migration status
    - Account creation status
    - Database verification report
    - Next steps for running the application

Troubleshooting:
    Issue: "ModuleNotFoundError: No module named 'django'"
    Solution: pip install django djangorestframework

    Issue: "No module named 'signtext'"
    Solution: Make sure you're in the backend directory

    Issue: "Database is locked"
    Solution: Close all Django servers and try again

    Issue: "User already exists"
    Solution: The script safely handles existing accounts

Modifying the Script:
    To add more test accounts:
        - Add to test_students list in main()
        - Or call create_student_account() directly

    To change instructor credentials:
        - Edit the email, password, and security_pin in main()
        - Update the display message accordingly

After Running:
    1. Start Django server: python manage.py runserver 127.0.0.1:8000
    2. Navigate to: http://localhost:3000/login.html
    3. Login with Maria's credentials above
    4. Access instructor dashboard at: http://localhost:3000/instructor-dashboard.html

Database Verification:
    The script shows:
    - Count of users, profiles, modules, announcements
    - List of instructor accounts
    - List of student accounts
    - List of learning modules
    - List of announcements

    This helps verify everything was created correctly.

Notes:
    - Student credentials are for testing/demo purposes
    - Instructor security PIN is required for login
    - All data is persisted in SQLite
    - The script is idempotent (safe to run multiple times)
    - Existing accounts are not recreated

For production:
    - Change password and PIN to secure values
    - Use environment variables for credentials
    - Consider using PostgreSQL instead of SQLite
    - Set up proper user management workflows
"""

# Script starts after this docstring - see setup_instructor_db.py file
