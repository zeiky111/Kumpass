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
    now = datetime.now().strftime('%Y%m%dT%H%M%S')
    db_path = os.path.abspath(os.path.join(PROJECT_BACKEND_DIR, 'db.sqlite3'))
    backup_path = db_path + f'.bak.{now}'

    if os.path.exists(db_path):
        try:
            import shutil
            shutil.copy2(db_path, backup_path)
            print(f'Backed up DB to: {backup_path}')
        except Exception as e:
            print('Failed to backup DB:', e)
            return
    else:
        print('Database file not found at', db_path)
        return

    admins = list(User.objects.filter(is_superuser=True))
    admin_emails = [u.email or u.username for u in admins]
    print('Admin users preserved:', admin_emails)

    to_delete_qs = User.objects.filter(is_superuser=False)
    delete_count = to_delete_qs.count()
    print(f'Users to delete: {delete_count}')
    # Print sample of emails to be deleted (up to 50)
    sample_emails = [u.email or u.username for u in to_delete_qs[:50]]
    if sample_emails:
        print('Sample to-delete emails:', sample_emails)

    # Perform deletion
    deleted_info = to_delete_qs.delete()
    print('Deletion result:', deleted_info)


if __name__ == '__main__':
    main()
