import os
import sys
from datetime import datetime

# Ensure backend package is importable
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_BACKEND_DIR = os.path.abspath(os.path.join(THIS_DIR, '..'))
if PROJECT_BACKEND_DIR not in sys.path:
    sys.path.insert(0, PROJECT_BACKEND_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kumpas_api.settings')
import django
django.setup()

from django.contrib.auth.models import User


def main():
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin1@kumpas.local').strip().lower()
    print('Preserving admin_email:', admin_email)

    admins = list(User.objects.filter(is_superuser=True))
    admin_emails = [u.email or u.username for u in admins]
    print('Existing superusers:', admin_emails)

    # Ensure admin_email exists
    preserve_qs = User.objects.filter(username__iexact=admin_email)
    if not preserve_qs.exists():
        print(f'Warning: specified admin_email {admin_email} not found as username. Proceeding to preserve superusers only.')
        to_delete_qs = User.objects.filter(is_superuser=False)
    else:
        to_delete_qs = User.objects.filter(is_superuser=False).exclude(username__iexact=admin_email)

    delete_count = to_delete_qs.count()
    print(f'Users to delete: {delete_count}')
    sample = [u.email or u.username for u in to_delete_qs[:50]]
    if sample:
        print('Sample to-delete emails:', sample)

    res = to_delete_qs.delete()
    print('Deletion result:', res)


if __name__ == '__main__':
    main()
