from django.conf import settings
from django.db import migrations

# Public registration only makes students, and Render's free plan has no
# shell to run create_staff_account, so the first admin/instructor accounts
# are seeded here. Only password hashes are stored, never the passwords.
STAFF_ACCOUNTS = [
    {
        "email": "admin@kumpas.com",
        "role": "admin",
        "first_name": "Kumpas",
        "last_name": "Admin",
        "password_hash": "pbkdf2_sha256$870000$3tVD2UogmvarNclaEzaiJy$I/vIgIlESVaTK+u727txDXZ9/il6lv6Km8F8G9j268w=",
    },
    {
        "email": "instructor@kumpas.com",
        "role": "instructor",
        "first_name": "Kumpas",
        "last_name": "Instructor",
        "password_hash": "pbkdf2_sha256$870000$cgcaMWgSKEznArZURlbxrh$1Q8W0UWKH8hLHipmSmeaE07AuwvERTRjGcyJFno/t5Y=",
    },
]


def seed_staff_accounts(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    UserProfile = apps.get_model("signtext", "UserProfile")
    UserLearningState = apps.get_model("signtext", "UserLearningState")

    for account in STAFF_ACCOUNTS:
        email = account["email"]
        user = User.objects.filter(username__iexact=email).first() or User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User(username=email, email=email)
        user.first_name = account["first_name"]
        user.last_name = account["last_name"]
        user.password = account["password_hash"]
        user.is_active = True
        user.is_staff = account["role"] == "admin"
        user.save()

        full_name = f"{account['first_name']} {account['last_name']}"
        profile = UserProfile.objects.filter(user=user).first() or UserProfile(user=user)
        profile.full_name = full_name
        profile.first_name = account["first_name"]
        profile.last_name = account["last_name"]
        profile.role = account["role"]
        profile.active = 0
        profile.year_level = ""
        profile.save()

        UserLearningState.objects.get_or_create(user=user)


class Migration(migrations.Migration):
    dependencies = [
        ("signtext", "0032_pool_remaining_sign_videos_into_existing_levels"),
    ]

    operations = [
        migrations.RunPython(seed_staff_accounts, migrations.RunPython.noop),
    ]
