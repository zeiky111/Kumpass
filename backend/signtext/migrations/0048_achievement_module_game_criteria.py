from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("signtext", "0047_module_certificate_achievement"),
    ]

    operations = [
        migrations.AlterField(
            model_name="achievement",
            name="criteria_type",
            field=models.CharField(
                choices=[
                    ("modules_completed", "Modules completed"),
                    ("streak_days", "Streak (days)"),
                    ("quiz_perfect_score", "Perfect quiz scores"),
                    ("quiz_count", "Quizzes taken"),
                    ("points_total", "Points total"),
                    ("module_passed", "Module post-test passed"),
                    ("game_passed", "Game passed (Hard)"),
                ],
                max_length=30,
            ),
        ),
    ]
