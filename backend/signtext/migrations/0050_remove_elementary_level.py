"""The Elementary level was removed (levels: Beginner -> Intermediate -> Advanced).

Any module already saved as Elementary becomes a Beginner module; the
curriculum's "Elementary – Everyday Vocabulary" module is renamed to
"Beginner – Everyday Vocabulary".
"""

from django.db import migrations


def forwards(apps, schema_editor):
    LearningModule = apps.get_model("signtext", "LearningModule")
    LearningModule.objects.filter(year_level="elementary").update(year_level="beginner")
    LearningModule.objects.filter(
        module_key="fsl-elementary", title="Elementary – Everyday Vocabulary"
    ).update(title="Beginner – Everyday Vocabulary")


class Migration(migrations.Migration):

    dependencies = [
        ("signtext", "0049_certificate_number_and_templates"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
