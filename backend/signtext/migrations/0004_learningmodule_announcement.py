from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_instructor_content(apps, schema_editor):
    LearningModule = apps.get_model("signtext", "LearningModule")
    Announcement = apps.get_model("signtext", "Announcement")
    User = apps.get_model("auth", "User")

    try:
        instructor = User.objects.filter(username="maria@ccnc.edu.ph").first()
    except Exception:
        instructor = None

    module_seed_data = [
        ("lesson1", "Lesson 1: Basic Finger Spelling", "1", "Start with the alphabet, hand positions, and visual recognition drills that support reading and spelling.", 4, "published", 1),
        ("lesson2", "Lesson 2: Common Everyday Signs", "1", "Build vocabulary for common communication needs such as greetings, thanks, requests, and polite expressions.", 5, "published", 2),
        ("lesson3", "Lesson 3: Greetings & Polite Expressions", "1", "Practice hello, how are you, thank you, sorry, and related forms of respectful interaction.", 3, "published", 3),
        ("lesson4", "Lesson 4: Family & Relationships", "2", "Learn signs for family, relatives, and relationship words that appear in daily conversation.", 6, "published", 4),
        ("lesson5", "Lesson 5: Numbers & Counting", "2", "Learn numerical signs, counting patterns, and number-based expressions used in practical settings.", 5, "published", 5),
        ("lesson6", "Lesson 6: Sign Language Grammar", "3", "Focus on word order, sentence patterns, and the grammar needed for understandable communication.", 8, "draft", 6),
        ("lesson7", "Lesson 7: Emotions & Expressions", "3", "Use signs for happy, sad, sorry, excited, and related emotions with correct expression.", 7, "draft", 7),
        ("lesson8", "Lesson 8: Complex Conversations", "4", "Apply learned signs in scenario-based dialogue, questions, responses, and more advanced communication.", 10, "draft", 8),
    ]

    for module_key, title, year_level, description, activities_count, status, sort_order in module_seed_data:
        LearningModule.objects.get_or_create(
            module_key=module_key,
            defaults={
                "title": title,
                "year_level": year_level,
                "description": description,
                "activities_count": activities_count,
                "status": status,
                "sort_order": sort_order,
                "created_by_id": instructor.id if instructor else None,
                "updated_by_id": instructor.id if instructor else None,
            },
        )

    if not Announcement.objects.exists():
        announcement_seed_data = [
            ("Updated: Module 5 - Advanced Signs", "Module 5 has been updated with new video content. All students should review the new lessons."),
            ("Reminder: Quiz This Friday!", "Don't forget - there's a quiz on Friday covering lessons 1-4. Make sure to review your notes."),
            ("New Achievement: Master Signer Badge", "Congratulations to all students who have earned the \"Master Signer\" badge this week!"),
        ]

        for title, message in announcement_seed_data:
            Announcement.objects.create(
                title=title,
                message=message,
                is_published=True,
                created_by_id=instructor.id if instructor else None,
                updated_by_id=instructor.id if instructor else None,
            )


def unseed_instructor_content(apps, schema_editor):
    LearningModule = apps.get_model("signtext", "LearningModule")
    Announcement = apps.get_model("signtext", "Announcement")
    LearningModule.objects.all().delete()
    Announcement.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("signtext", "0003_userlearningstate"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LearningModule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("module_key", models.CharField(max_length=64, unique=True)),
                ("title", models.CharField(max_length=180)),
                ("year_level", models.CharField(default="1", max_length=20)),
                ("description", models.TextField(blank=True, default="")),
                ("activities_count", models.PositiveIntegerField(default=0)),
                (
                    "status",
                    models.CharField(
                        choices=[("draft", "Draft"), ("published", "Published"), ("archived", "Archived")],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_learning_modules",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="updated_learning_modules",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["sort_order", "title"]},
        ),
        migrations.CreateModel(
            name="Announcement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("message", models.TextField()),
                ("is_published", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_announcements",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="updated_announcements",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.RunPython(seed_instructor_content, unseed_instructor_content),
    ]