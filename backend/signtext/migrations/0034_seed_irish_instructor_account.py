from django.conf import settings
from django.db import migrations

# Restore the irish@gmail.com instructor login on the live database, which
# had no matching account. Existing name/profile details are kept; only the
# password, role and active flags are set. Only the password hash is stored.
EMAIL = "irish@gmail.com"
PASSWORD_HASH = "pbkdf2_sha256$870000$fbMuFzwqEBkgpa5DGfgOSM$8ajC5+M/rXT06cXyX4TMK0SezT9NM6pFAMCFe+rVkzk="


def seed_irish_instructor(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    UserProfile = apps.get_model("signtext", "UserProfile")
    UserLearningState = apps.get_model("signtext", "UserLearningState")

    user = User.objects.filter(username__iexact=EMAIL).first() or User.objects.filter(email__iexact=EMAIL).first()
    if user is None:
        user = User(username=EMAIL, email=EMAIL, first_name="Irish", last_name="Instructor")
    user.password = PASSWORD_HASH
    user.is_active = True
    user.save()

    profile = UserProfile.objects.filter(user=user).first()
    if profile is None:
        profile = UserProfile(
            user=user,
            full_name=f"{user.first_name} {user.last_name}".strip() or "Irish",
            first_name=user.first_name,
            last_name=user.last_name,
        )
    profile.role = "instructor"
    profile.active = 0
    profile.year_level = ""
    profile.save()

    UserLearningState.objects.get_or_create(user=user)


class Migration(migrations.Migration):
    dependencies = [
        ("signtext", "0033_seed_staff_accounts"),
    ]

    operations = [
        migrations.RunPython(seed_irish_instructor, migrations.RunPython.noop),
    ]
