from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from signtext.models import UserLearningState, UserProfile

ROLES = ("admin", "instructor")


class Command(BaseCommand):
    """Create (or reset) an admin/instructor account.

    Public registration always creates students, so staff accounts are made
    here. Re-running with the same email resets the password and role.

    Example:
        python manage.py create_staff_account --role admin \
            --email admin@kumpas.com --password "S3cret-pass" \
            --first-name Kumpas --last-name Admin
    """

    help = "Create or reset an admin/instructor account"

    def add_arguments(self, parser):
        parser.add_argument("--role", required=True, choices=ROLES)
        parser.add_argument("--email", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--first-name", default="")
        parser.add_argument("--last-name", default="")

    def handle(self, *args, **options):
        role = options["role"]
        email = options["email"].strip().lower()
        password = options["password"]
        if not email:
            raise CommandError("Email is required")
        if len(password) < 8:
            raise CommandError("Password must be at least 8 characters")

        first_name = options["first_name"].strip() or role.capitalize()
        last_name = options["last_name"].strip() or "Kumpas"

        user = User.objects.filter(username__iexact=email).first() or User.objects.filter(email__iexact=email).first()
        created = user is None
        if created:
            user = User(username=email, email=email)
        user.first_name = first_name
        user.last_name = last_name
        user.is_active = True
        user.is_staff = role == "admin"
        user.set_password(password)
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={"full_name": f"{first_name} {last_name}"})
        profile.first_name = first_name
        profile.last_name = last_name
        profile.role = role
        profile.active = 0
        profile.year_level = ""
        profile.save()

        UserLearningState.objects.get_or_create(user=user)

        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} {role} account: {user.username}"))
