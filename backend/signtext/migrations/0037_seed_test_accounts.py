from django.conf import settings
from django.db import migrations

# Extra test logins on the live database: one student per year level and a
# second instructor. Only password hashes are stored, never the passwords.
TEST_ACCOUNTS = [
    {
        "email": "student2@kumpas.com",
        "role": "student",
        "first_name": "Student",
        "last_name": "Year1",
        "year_level": "1",
        "password_hash": "pbkdf2_sha256$870000$HxFuRvTDuwch47ryCNLIq2$3zzr0YKyWFci1aIk/Cw27TVlUyKyExjECB2S1Sdfz0M=",
    },
    {
        "email": "student3@kumpas.com",
        "role": "student",
        "first_name": "Student",
        "last_name": "Year2",
        "year_level": "2",
        "password_hash": "pbkdf2_sha256$870000$sYMZUBZCAWpnSyEUhjWRDt$a26rtUBp60Glp7COFEl70fqNuzQGuk2Zf3xtWjwyB4o=",
    },
    {
        "email": "student4@kumpas.com",
        "role": "student",
        "first_name": "Student",
        "last_name": "Year3",
        "year_level": "3",
        "password_hash": "pbkdf2_sha256$870000$9yK33JPL044h82TkSagyV5$JmYmu8LWH1FjMkYZenQbvkDlcZoAHoSeSyJL9tDpymA=",
    },
    {
        "email": "student5@kumpas.com",
        "role": "student",
        "first_name": "Student",
        "last_name": "Year4",
        "year_level": "4",
        "password_hash": "pbkdf2_sha256$870000$w94bqHWx5Qxaby0PP03ZjP$Z1Y7t8m52/cgHm5kB+Eah+Fwv+yXWt/bGSB6V4Z/5vA=",
    },
    {
        "email": "instructor2@kumpas.com",
        "role": "instructor",
        "first_name": "Kumpas",
        "last_name": "Instructor 2",
        "year_level": "",
        "password_hash": "pbkdf2_sha256$870000$n3U8QyLFMfMINHzWOxJ2wd$hcEwYY9BTnZ4o/MjaLOvGWIyy5rEdeiNMCiGMBmZFkU=",
    },
]


def seed_test_accounts(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    UserProfile = apps.get_model("signtext", "UserProfile")
    UserLearningState = apps.get_model("signtext", "UserLearningState")

    for account in TEST_ACCOUNTS:
        email = account["email"]
        user = User.objects.filter(username__iexact=email).first() or User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User(username=email, email=email)
        user.first_name = account["first_name"]
        user.last_name = account["last_name"]
        user.password = account["password_hash"]
        user.is_active = True
        user.is_staff = False
        user.save()

        profile = UserProfile.objects.filter(user=user).first() or UserProfile(user=user)
        profile.full_name = f"{account['first_name']} {account['last_name']}"
        profile.first_name = account["first_name"]
        profile.last_name = account["last_name"]
        profile.role = account["role"]
        profile.active = 0
        profile.year_level = account["year_level"]
        profile.save()

        UserLearningState.objects.get_or_create(user=user)


class Migration(migrations.Migration):
    dependencies = [
        ("signtext", "0036_seed_admin1_account"),
    ]

    operations = [
        migrations.RunPython(seed_test_accounts, migrations.RunPython.noop),
    ]
