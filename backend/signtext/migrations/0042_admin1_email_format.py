from django.conf import settings
from django.db import migrations

OLD_USERNAME = "admin1"
NEW_EMAIL = "admin1@kumpas.com"


def set_admin_email(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    user = (
        User.objects.filter(username__iexact=OLD_USERNAME).first()
        or User.objects.filter(username__iexact=NEW_EMAIL).first()
    )
    if user is None:
        return
    user.username = NEW_EMAIL
    user.email = NEW_EMAIL
    user.save(update_fields=["username", "email"])


def revert_admin_email(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    user = User.objects.filter(username__iexact=NEW_EMAIL).first()
    if user is None:
        return
    user.username = OLD_USERNAME
    user.email = ""
    user.save(update_fields=["username", "email"])


class Migration(migrations.Migration):
    dependencies = [
        ("signtext", "0041_seed_announcements"),
    ]

    operations = [
        migrations.RunPython(set_admin_email, revert_admin_email),
    ]
