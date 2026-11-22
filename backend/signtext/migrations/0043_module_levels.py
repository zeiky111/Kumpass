from django.db import migrations, models

# Modules move from 1st-4th Year to two learner levels.
YEAR_TO_LEVEL = {"1": "beginner", "2": "beginner", "3": "intermediate", "4": "intermediate"}


def years_to_levels(apps, schema_editor):
    LearningModule = apps.get_model("signtext", "LearningModule")
    for module in LearningModule.objects.all():
        current = str(module.year_level or "").strip().lower()
        level = YEAR_TO_LEVEL.get(current, current if current in {"beginner", "intermediate"} else "beginner")
        if level != module.year_level:
            module.year_level = level
            module.save(update_fields=["year_level"])


class Migration(migrations.Migration):
    dependencies = [
        ("signtext", "0042_admin1_email_format"),
    ]

    operations = [
        migrations.AlterField(
            model_name="learningmodule",
            name="year_level",
            field=models.CharField(default="beginner", max_length=20),
        ),
        migrations.RunPython(years_to_levels, migrations.RunPython.noop),
    ]
