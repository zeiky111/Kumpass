import random
from datetime import timedelta

from django.conf import settings
from django.db import migrations
from django.utils import timezone

# Sample learning progress for the student accounts seeded in 0037-0039, so
# the admin and instructor reports have data to show. Values are generated
# from a seed per email, so every run gives the same numbers. A student who
# already has points (real activity) is left alone. Each filled state is
# marked "sampleData": True so it can be found and cleared later.
STUDENT_EMAILS = [
    "student2@kumpas.com", "student3@kumpas.com", "student4@kumpas.com", "student5@kumpas.com",
    "aldaczarajoy@gmail.com", "kimhernandezalda@gmail.com",
    "jhonlloyd.abad@gmail.com", "maangela.rivera08@gmail.com", "kurt.esguerra.2006@gmail.com",
    "ellamae.fajardo1@gmail.com", "justine.concepcion@gmail.com", "rachelle.mallari06@gmail.com",
    "giancarlo.bueno.2006@gmail.com", "patricia.lim4@gmail.com", "ivan.manzano@gmail.com",
    "jasmine.tan04@gmail.com", "arvin.castro.2006@gmail.com", "clarisse.domingo7@gmail.com",
    "noel.serrano@gmail.com", "danica.perez02@gmail.com", "rafael.belen.2006@gmail.com",
    "joanna.vergara1@gmail.com", "emmanuel.quinto@gmail.com", "ysabel.hernandez30@gmail.com",
    "kevin.lacsamana.2006@gmail.com", "apriljoy.montero4@gmail.com", "cedric.bacani@gmail.com",
    "aira.saldivar28@gmail.com", "miguel.roxas.2006@gmail.com", "charmaine.agustin7@gmail.com",
    "jayson.delmundo@gmail.com", "precious.marquez26@gmail.com", "aldrin.gatdula.2006@gmail.com",
    "louise.cortez1@gmail.com", "zyrus.maglaque@gmail.com", "kimberly.arellano24@gmail.com",
]

FALLBACK_MODULE_KEYS = ["lesson1", "lesson2", "lesson3", "lesson4"]
ACTIVITIES = [
    ("🎮", "Sign Match completed"),
    ("⌨️", "Typing Game completed"),
    ("🧩", "Sentence Builder completed"),
    ("🎭", "Scenario Game completed"),
    ("📘", "Module lesson reviewed"),
    ("📝", "Module quiz submitted"),
]


def _rank(points):
    # Same thresholds as calculateRank() in js/portal.js.
    if points <= 0:
        return 0
    for minimum, rank in ((4000, 1), (3500, 3), (3000, 5), (2500, 8), (2000, 12), (1500, 18)):
        if points >= minimum:
            return rank
    return 24


def _module_keys_by_year(LearningModule):
    published = list(LearningModule.objects.filter(status="published").values_list("module_key", "year_level"))
    by_year = {}
    for key, year in published:
        by_year.setdefault(str(year or "1"), []).append(key)
    all_keys = [key for key, _ in published]
    return by_year, all_keys


def _sample_state(rng, module_keys, quiz_keys):
    # Taking a module's quiz marks the module 100% complete (see
    # submit_module_quiz), so most quiz modules are completed here.
    progress = {
        key: (100 if rng.random() < 0.75 else rng.choice([75, 50, 25, 0]))
        if key in quiz_keys
        else rng.choice([100, 100, 100, 75, 75, 50, 50, 25, 0])
        for key in module_keys
    }
    total_progress = sum(progress.values())
    points = 120 + total_progress * rng.randint(4, 9) + rng.randint(0, 300)
    completed_activities = max(1, total_progress // 25 + rng.randint(0, 6))
    activities = rng.sample(ACTIVITIES, 3)
    return {
        "points": points,
        "rank": _rank(points),
        "accuracy": rng.randint(62, 96),
        "streak": rng.randint(0, 12),
        "completedActivities": completed_activities,
        "practiceMinutes": completed_activities * rng.randint(8, 15),
        "weeklyActivity": [rng.randint(0, 5) for _ in range(7)],
        "moduleProgress": progress,
        "recentActivity": [
            {"icon": icon, "text": text, "meta": f"+{rng.randint(20, 80)} points"} for icon, text in activities
        ],
        "achievements": [],
        "leaderboard": [],
        "performance": [],
        "sampleData": True,
    }


def seed_sample_progress(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    UserProfile = apps.get_model("signtext", "UserProfile")
    UserLearningState = apps.get_model("signtext", "UserLearningState")
    LearningModule = apps.get_model("signtext", "LearningModule")
    QuizQuestion = apps.get_model("signtext", "QuizQuestion")
    QuizAttempt = apps.get_model("signtext", "QuizAttempt")

    by_year, all_keys = _module_keys_by_year(LearningModule)
    # Published modules that have quiz questions, keyed by module_key, with
    # their question count (the "total" of an attempt).
    quiz_modules = {}
    for module in LearningModule.objects.filter(status="published"):
        question_count = QuizQuestion.objects.filter(module=module).count()
        if question_count:
            quiz_modules[module.module_key] = (module, question_count)
    now = timezone.now()

    for email in STUDENT_EMAILS:
        user = User.objects.filter(username__iexact=email).first()
        if user is None:
            continue
        profile = UserProfile.objects.filter(user=user).first()
        if profile is None or str(profile.role or "").lower() != "student":
            continue

        learning_state, _ = UserLearningState.objects.get_or_create(user=user)
        current = learning_state.state if isinstance(learning_state.state, dict) else {}
        try:
            has_activity = int(current.get("points") or 0) > 0
        except (TypeError, ValueError):
            has_activity = False
        if has_activity:
            continue

        year = str(profile.year_level or "1")
        module_keys = by_year.get(year) or all_keys or FALLBACK_MODULE_KEYS
        rng = random.Random(email.lower())
        state = _sample_state(rng, module_keys, set(quiz_modules))
        learning_state.state = state
        learning_state.save()

        # One quiz attempt per completed quiz module, mostly passing scores,
        # dated over the last few weeks. No certificates are awarded here,
        # since awarding one emails the student.
        for key, value in state["moduleProgress"].items():
            if value < 100 or key not in quiz_modules:
                continue
            module, total = quiz_modules[key]
            if QuizAttempt.objects.filter(user=user, module=module).exists():
                continue
            low = max(0, round(total * 0.5))
            score = rng.randint(low, total) if rng.random() < 0.3 else rng.randint(max(low, -(-total * 3 // 4)), total)
            attempt = QuizAttempt.objects.create(user=user, module=module, score=score, total=total)
            submitted = now - timedelta(days=rng.randint(1, 28), hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
            QuizAttempt.objects.filter(pk=attempt.pk).update(created_at=submitted)


class Migration(migrations.Migration):
    dependencies = [
        ("signtext", "0039_seed_school_accounts"),
    ]

    operations = [
        migrations.RunPython(seed_sample_progress, migrations.RunPython.noop),
    ]
