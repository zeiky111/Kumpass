"""Per-level Certificate of Completion (Beginner / Intermediate / Advanced)."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("signtext", "0050_remove_elementary_level"),
    ]

    operations = [
        migrations.AddField(
            model_name="certificate",
            name="level",
            field=models.CharField(blank=True, max_length=20, null=True, unique=True),
        ),
    ]
