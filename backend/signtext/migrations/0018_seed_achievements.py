from django.db import migrations


ACHIEVEMENTS = [
    {
        "key": "first_module",
        "name": "First Steps",
        "icon": "fa-solid fa-graduation-cap",
        "criteria_type": "modules_completed",
        "criteria_value": 1,
        "sort_order": 10,
    },
    {
        "key": "five_modules",
        "name": "Dedicated Learner",
        "icon": "fa-solid fa-graduation-cap",
        "criteria_type": "modules_completed",
        "criteria_value": 5,
        "sort_order": 20,
    },
    {
        "key": "all_modules",
        "name": "Module Master",
        "icon": "fa-solid fa-graduation-cap",
        "criteria_type": "modules_completed",
        "criteria_value": 8,
        "sort_order": 30,
    },
    {
        "key": "week_streak",
        "name": "Week Warrior",
        "icon": "fa-solid fa-fire",
        "criteria_type": "streak_days",
        "criteria_value": 7,
        "sort_order": 40,
    },
    {
        "key": "perfect_quiz",
        "name": "Perfect Score",
        "icon": "fa-solid fa-star",
        "criteria_type": "quiz_perfect_score",
        "criteria_value": 1,
        "sort_order": 50,
    },
    {
        "key": "quiz_veteran",
        "name": "Quiz Veteran",
        "icon": "fa-solid fa-star",
        "criteria_type": "quiz_count",
        "criteria_value": 10,
        "sort_order": 60,
    },
    {
        "key": "point_climber",
        "name": "Point Climber",
        "icon": "fa-solid fa-bolt",
        "criteria_type": "points_total",
        "criteria_value": 500,
        "sort_order": 70,
    },
    {
        "key": "point_master",
        "name": "Point Master",
        "icon": "fa-solid fa-bolt",
        "criteria_type": "points_total",
        "criteria_value": 2000,
        "sort_order": 80,
    },
]


def seed_achievements(apps, schema_editor):
    Achievement = apps.get_model("signtext", "Achievement")
    for entry in ACHIEVEMENTS:
        Achievement.objects.update_or_create(key=entry["key"], defaults=entry)


def remove_achievements(apps, schema_editor):
    Achievement = apps.get_model("signtext", "Achievement")
    Achievement.objects.filter(key__in=[entry["key"] for entry in ACHIEVEMENTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("signtext", "0017_achievement_quizattempt_userachievement_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_achievements, remove_achievements),
    ]
