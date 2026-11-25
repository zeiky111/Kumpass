"""Certificate numbers, and the new certificate templates.

* UserCertificate.certificate_number: system-generated number printed on the
  certificate (e.g. KMP-2026-0727-0001) so it can be verified in KUMPAS.
* Games give a "Certificate of Achievement" (one template per game) and
  finishing every learning module gives a "Certificate of Completion".
  Existing catalog entries are pointed at the new templates/titles.
  Certificates already issued (their PDFs) are left as they are.
"""

from django.db import migrations, models

GAME_TEMPLATES = {
    "sign_match": ("images/cert-game-sign-match.png", "Sign Match Game — Certificate of Achievement"),
    "typing": ("images/cert-game-typing.png", "Sign-to-Word Game — Certificate of Achievement"),
    "sentence": ("images/cert-game-sentence.png", "Sentence Builder Game — Certificate of Achievement"),
    "scenario": ("images/cert-game-scenario.png", "Scenario-Based Game — Certificate of Achievement"),
}
MODULES_TEMPLATE = "images/cert-modules-completion.png"
MODULES_TITLE = "Kumpas Learning Modules — Certificate of Completion"


def forwards(apps, schema_editor):
    Certificate = apps.get_model("signtext", "Certificate")
    for game_key, (template, title) in GAME_TEMPLATES.items():
        Certificate.objects.filter(game_key=game_key).update(template_path=template, title=title)
    Certificate.objects.filter(game_key__isnull=True, module__isnull=True).update(
        template_path=MODULES_TEMPLATE, title=MODULES_TITLE
    )


class Migration(migrations.Migration):

    dependencies = [
        ("signtext", "0048_achievement_module_game_criteria"),
    ]

    operations = [
        migrations.AddField(
            model_name="usercertificate",
            name="certificate_number",
            field=models.CharField(blank=True, max_length=32, null=True, unique=True),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
