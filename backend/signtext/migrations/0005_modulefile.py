from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("signtext", "0004_learningmodule_announcement"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ModuleFile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file_name", models.CharField(max_length=255)),
                ("file", models.FileField(upload_to="module_files/%Y/%m/%d/")),
                (
                    "file_type",
                    models.CharField(
                        choices=[
                            ("document", "Document (PDF, Word, etc.)"),
                            ("presentation", "Presentation (PPT, etc.)"),
                            ("video", "Video"),
                            ("image", "Image"),
                            ("audio", "Audio"),
                            ("other", "Other"),
                        ],
                        default="document",
                        max_length=20,
                    ),
                ),
                ("file_size", models.PositiveIntegerField(default=0)),
                ("description", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "module",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="files", to="signtext.learningmodule"),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="uploaded_module_files",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Module File",
                "verbose_name_plural": "Module Files",
                "ordering": ["-created_at"],
            },
        ),
    ]
