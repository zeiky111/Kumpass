from django.conf import settings
from django.db import migrations

# A ready-to-use student login on the live database, alongside the seeded
# staff accounts. Only the password hash is stored.
EMAIL = "student@kumpas.com"
PASSWORD_HASH = "pbkdf2_sha256$870000$z9dDiRylyZpLWhhb40YjAK$vGu1El0rYgbKRpQaowl01yCGNRUnx7/YRlT3pCK/UII="


def seed_student_account(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    UserProfile = apps.get_model("signtext", "UserProfile")
    UserLearningState = apps.get_model("signtext", "UserLearningState")

    user = User.objects.filter(username__iexact=EMAIL).first() or User.objects.filter(email__iexact=EMAIL).first()
    if user is None:
        user = User(username=EMAIL, email=EMAIL, first_name="Kumpas", last_name="Student")
    user.password = PASSWORD_HASH
    user.is_active = True
    user.save()

    profile = UserProfile.objects.filter(user=user).first()
    if profile is None:
        profile = UserProfile(
            user=user,
            full_name=f"{user.first_name} {user.last_name}".strip(),
            first_name=user.first_name,
            last_name=user.last_name,
            year_level="1",
        )
    profile.role = "student"
    profile.active = 0
    profile.save()

    UserLearningState.objects.get_or_create(user=user)


class Migration(migrations.Migration):
    dependencies = [
        ("signtext", "0034_seed_irish_instructor_account"),
    ]

    operations = [
        migrations.RunPython(seed_student_account, migrations.RunPython.noop),
    ]
