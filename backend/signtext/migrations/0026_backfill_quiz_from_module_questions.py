"""Backfill an implicit published Quiz for every module that already has
quiz questions and/or graded attempts, so existing student-facing quizzes
keep working unchanged after QuizQuestion/QuizAttempt start pointing at the
new Quiz model instead of being read directly off the module.

is_published=True is correct here, not just a default: these questions were
already live to students with zero draft gate before this change, so this
migration makes the existing implicit state explicit without changing
anything students can see. No certificates are retroactively awarded.
"""
from django.db import migrations

DEFAULT_PASSING_SCORE = 60


def backfill_quizzes(apps, schema_editor):
    LearningModule = apps.get_model("signtext", "LearningModule")
    QuizQuestion = apps.get_model("signtext", "QuizQuestion")
    QuizAttempt = apps.get_model("signtext", "QuizAttempt")
    Quiz = apps.get_model("signtext", "Quiz")
    QuizQuestionLink = apps.get_model("signtext", "QuizQuestionLink")

    module_ids_with_questions = set(
        QuizQuestion.objects.filter(module__isnull=False).values_list("module_id", flat=True)
    )
    module_ids_with_attempts = set(QuizAttempt.objects.values_list("module_id", flat=True))
    module_ids = module_ids_with_questions | module_ids_with_attempts

    for module in LearningModule.objects.filter(id__in=module_ids):
        quiz = Quiz.objects.create(
            module=module,
            title=f"{module.title} Quiz",
            passing_score=DEFAULT_PASSING_SCORE,
            is_published=True,
        )

        questions = QuizQuestion.objects.filter(module=module).order_by("order", "created_at")
        QuizQuestionLink.objects.bulk_create(
            [
                QuizQuestionLink(quiz=quiz, question=question, order=question.order)
                for question in questions
            ]
        )

        for attempt in QuizAttempt.objects.filter(module=module):
            attempt.quiz = quiz
            attempt.passed = bool(attempt.total) and (
                (attempt.score / attempt.total * 100) >= DEFAULT_PASSING_SCORE
            )
            attempt.save(update_fields=["quiz", "passed"])


def remove_backfilled_quizzes(apps, schema_editor):
    QuizAttempt = apps.get_model("signtext", "QuizAttempt")
    Quiz = apps.get_model("signtext", "Quiz")

    QuizAttempt.objects.update(quiz=None, passed=False)
    Quiz.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("signtext", "0025_quizquestionlink_quizattempt_passed_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_quizzes, remove_backfilled_quizzes),
    ]
