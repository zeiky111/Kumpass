import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from signtext.models import UserLearningState, UserProfile

ROLES = ("admin", "instructor")


def ensure_staff_account(role: str, email: str, password: str, first_name: str = "", last_name: str = "") -> bool:
    """Create the account, or reset its password/role if it exists. Returns True if created."""
    email = email.strip().lower()
    if role not in ROLES:
        raise ValueError(f"Role must be one of {ROLES}")
    if not email:
        raise ValueError("Email is required")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    first_name = first_name.strip() or role.capitalize()
    last_name = last_name.strip() or "Kumpas"

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
    return created


def ensure_staff_accounts_from_env() -> list[str]:
    """Apply KUMPAS_ADMIN_EMAIL/PASSWORD and KUMPAS_INSTRUCTOR_EMAIL/PASSWORD if set.

    Lets staff accounts be created on hosts without a shell (e.g. Render's free
    plan) by setting environment variables. Runs on every boot, so the env
    password wins over one changed in the app; unset the vars to stop that.
    """
    applied = []
    for role in ROLES:
        email = os.getenv(f"KUMPAS_{role.upper()}_EMAIL", "").strip()
        password = os.getenv(f"KUMPAS_{role.upper()}_PASSWORD", "")
        if email and password:
            ensure_staff_account(role, email, password)
            applied.append(f"{role}:{email.lower()}")
    return applied


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
        try:
            created = ensure_staff_account(
                options["role"],
                options["email"],
                options["password"],
                options["first_name"],
                options["last_name"],
            )
        except ValueError as exc:
            raise CommandError(str(exc))

        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} {options['role']} account: {options['email'].strip().lower()}"))
