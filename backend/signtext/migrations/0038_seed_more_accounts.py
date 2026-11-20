from django.conf import settings
from django.db import migrations

# More logins on the live database. Only password hashes are stored.
# If an account already exists, its name is kept and only the password,
# role and year level are set.
ACCOUNTS = [
    {
        "email": "aldaczarajoy@gmail.com",
        "role": "student",
        "first_name": "Czara Joy",
        "last_name": "Alda",
        "year_level": "2",
        "password_hash": "pbkdf2_sha256$870000$KD4OxTNTlnNiGLzLvyM5Tc$W2yYgstDr+3pB8LJTVgN8/PKXiXVh0nzxWAmTJDTmAc=",
    },
    {
        "email": "kimhernandezalda@gmail.com",
        "role": "student",
        "first_name": "Kim Hernandez",
        "last_name": "Alda",
        "year_level": "3",
        "password_hash": "pbkdf2_sha256$870000$uuRoQrDV13SzxHXndXGk1G$eVcYYs+us3RW10vNmSAl0g+IJO8PtBLmTYAdvbBn2Xs=",
    },
    {
        "email": "magandiajericho@gmail.com",
        "role": "instructor",
        "first_name": "Jericho",
        "last_name": "Magandia",
        "year_level": "",
        "password_hash": "pbkdf2_sha256$870000$Eyp3UN2tlPb15lXSsxDEcv$tkdgsg2yxF9bg717NWx/LFymyQ/rHwQM/fsS+fv9OjM=",
    },
]


def seed_accounts(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    UserProfile = apps.get_model("signtext", "UserProfile")
    UserLearningState = apps.get_model("signtext", "UserLearningState")

    for account in ACCOUNTS:
        email = account["email"]
        user = User.objects.filter(username__iexact=email).first() or User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User(username=email, email=email, first_name=account["first_name"], last_name=account["last_name"])
        user.password = account["password_hash"]
        user.is_active = True
        user.save()

        profile = UserProfile.objects.filter(user=user).first()
        if profile is None:
            profile = UserProfile(
                user=user,
                full_name=f"{user.first_name} {user.last_name}".strip(),
                first_name=user.first_name,
                last_name=user.last_name,
            )
        profile.role = account["role"]
        profile.active = 0
        profile.year_level = account["year_level"]
        profile.save()

        UserLearningState.objects.get_or_create(user=user)


class Migration(migrations.Migration):
    dependencies = [
        ("signtext", "0037_seed_test_accounts"),
    ]

    operations = [
        migrations.RunPython(seed_accounts, migrations.RunPython.noop),
    ]
