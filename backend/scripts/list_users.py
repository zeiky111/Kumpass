import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_BACKEND_DIR = os.path.abspath(os.path.join(THIS_DIR, '..'))
if PROJECT_BACKEND_DIR not in sys.path:
    sys.path.insert(0, PROJECT_BACKEND_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kumpas_api.settings')
import django
django.setup()

from django.contrib.auth.models import User

def main():
    users = User.objects.all()
    print('Total users:', users.count())
    for u in users:
        print('username={0} email={1} is_superuser={2} is_staff={3}'.format(u.username, u.email, u.is_superuser, u.is_staff))

if __name__ == '__main__':
    main()
