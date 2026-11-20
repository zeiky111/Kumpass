from datetime import timedelta

from django.conf import settings
from django.db import migrations
from django.utils import timezone

# Starter announcements for the live site, posted by the seeded admin and
# instructor accounts and dated over the past few weeks. An announcement
# whose title already exists is skipped, so edits made in the app are kept.
ANNOUNCEMENTS = [
    {
        "author": "admin@kumpas.com",
        "days_ago": 27,
        "title": "Welcome to Kumpas!",
        "message": (
            "Welcome to Kumpas, your space for learning Filipino Sign Language (FSL). "
            "Start with the modules for your year level under Learning, practice with the games, "
            "and track your progress on your dashboard. If you have questions about your account, "
            "message your instructor or the admin."
        ),
    },
    {
        "author": "instructor@kumpas.com",
        "days_ago": 21,
        "title": "Learning modules are now open for all year levels",
        "message": (
            "Modules for 1st to 4th year are now published. "
            "1st Year: Introduction to Sign Language, Sign Language 101, and Deaf Culture and Etiquette. "
            "2nd Year: FSL Grammar Basics, and Classifiers and the Signing Space. "
            "3rd Year: Deaf History and Education in the Philippines, and Sign Language Interpreting and Accessibility. "
            "4th Year: Disability Rights and Inclusion in the Philippines, and Sign Language Technology and Ethics. "
            "Go through the lesson materials before taking each module's quiz."
        ),
    },
    {
        "author": "instructor@kumpas.com",
        "days_ago": 18,
        "title": "Module quiz reminders",
        "message": (
            "Each module has a 10-item quiz. You can take each quiz only once, so review the "
            "lesson materials first and make sure your internet connection is stable before you start. "
            "A score of 75% or higher is a passing mark. Finishing a quiz marks the module as complete."
        ),
    },
    {
        "author": "admin@kumpas.com",
        "days_ago": 12,
        "title": "Earn certificates for completed modules",
        "message": (
            "You can now earn a certificate when you complete a module and its quiz. "
            "Your certificates appear on your Profile page, where you can download them anytime. "
            "Keep going and collect them all!"
        ),
    },
    {
        "author": "instructor@kumpas.com",
        "days_ago": 8,
        "title": "Practice with the sign games",
        "message": (
            "Sharpen your signing with the Sign Match Game, the Sign-to-Word Typing Game, the Sentence Builder Game, "
            "and the Scenario-Based Game "
            "under Games. Each game you finish adds points to your account and moves you up the leaderboard. "
            "A few minutes of practice every day keeps your streak going."
        ),
    },
    {
        "author": "instructor@kumpas.com",
        "days_ago": 3,
        "title": "International Day of Persons with Disabilities - December 3",
        "message": (
            "December 3 is the International Day of Persons with Disabilities. "
            "Take this week to learn more about the Deaf community and accessibility in the Philippines: "
            "review the Deaf Culture and Etiquette and Disability Rights and Inclusion modules, "
            "and practice greeting and introducing yourself in FSL."
        ),
    },
    {
        "author": "admin@kumpas.com",
        "days_ago": 1,
        "title": "Account and login reminders",
        "message": (
            "Do not share your password with anyone. If you forget it, use Forgot Password on the login page "
            "to reset it through your email. If you signed up with Google, use Sign in with Google. "
            "Make sure your year level on your profile is correct so you see the right modules."
        ),
    },
]


def seed_announcements(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    Announcement = apps.get_model("signtext", "Announcement")

    now = timezone.now()
    for item in ANNOUNCEMENTS:
        if Announcement.objects.filter(title=item["title"]).exists():
            continue
        author = User.objects.filter(username__iexact=item["author"]).first()
        announcement = Announcement.objects.create(
            title=item["title"],
            message=item["message"],
            is_published=True,
            created_by=author,
            updated_by=author,
        )
        posted = now - timedelta(days=item["days_ago"])
        Announcement.objects.filter(pk=announcement.pk).update(created_at=posted, updated_at=posted)


class Migration(migrations.Migration):
    dependencies = [
        ("signtext", "0040_seed_sample_student_progress"),
    ]

    operations = [
        migrations.RunPython(seed_announcements, migrations.RunPython.noop),
    ]
