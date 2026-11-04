from django.conf import settings
from django.db import migrations

# The "admin1" admin login on the live database. Only the password hash is
# stored. Existing name/profile details are kept if the account exists.
USERNAME = "admin1"
PASSWORD_HASH = "pbkdf2_sha256$870000$yLthfjVR4LrbAwbPRNvTxi$nHR6OI+z31mhCTz+4jz/ozTWzhvfDdN42tU7FfLksEs="


def seed_admin1(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    UserProfile = apps.get_model("signtext", "UserProfile")
    UserLearningState = apps.get_model("signtext", "UserLearningState")

    user = User.objects.filter(username__iexact=USERNAME).first()
    if user is None:
        user = User(username=USERNAME, email="", first_name="Kumpas", last_name="Admin")
    user.password = PASSWORD_HASH
    user.is_active = True
    user.is_staff = True
    user.save()

    profile = UserProfile.objects.filter(user=user).first()
    if profile is None:
        profile = UserProfile(
            user=user,
            full_name=f"{user.first_name} {user.last_name}".strip() or USERNAME,
            first_name=user.first_name,
            last_name=user.last_name,
        )
    profile.role = "admin"
    profile.active = 0
    profile.year_level = ""
    profile.save()

    UserLearningState.objects.get_or_create(user=user)


class Migration(migrations.Migration):
    dependencies = [
        ("signtext", "0035_seed_student_account"),
    ]

    operations = [
        migrations.RunPython(seed_admin1, migrations.RunPython.noop),
    ]
