from django.db import migrations


CERTIFICATES = [
    {
        "game_key": "sign_match",
        "title": "Sign Match Game",
        "template_path": "images/2.png",
    },
    {
        "game_key": "typing",
        "title": "Sign-to-Word Typing Game",
        "template_path": "images/3.png",
    },
    {
        "game_key": "sentence",
        "title": "Sentence Builder Game",
        "template_path": "images/4.png",
    },
    {
        "game_key": "scenario",
        "title": "Scenario-Based Game",
        "template_path": "images/5.png",
    },
]


def seed_certificates(apps, schema_editor):
    Certificate = apps.get_model("signtext", "Certificate")
    for entry in CERTIFICATES:
        Certificate.objects.update_or_create(game_key=entry["game_key"], defaults=entry)


def remove_certificates(apps, schema_editor):
    Certificate = apps.get_model("signtext", "Certificate")
    Certificate.objects.filter(game_key__in=[entry["game_key"] for entry in CERTIFICATES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("signtext", "0020_certificate_models"),
    ]

    operations = [
        migrations.RunPython(seed_certificates, remove_certificates),
    ]
