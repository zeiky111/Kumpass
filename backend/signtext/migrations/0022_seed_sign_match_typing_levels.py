import os

from django.db import migrations


# Matches the convention in 0019_seed_sentence_scenario_levels.py.
MEDIA_BASE_URL = os.getenv("KUMPAS_MEDIA_BASE_URL", "https://kumpass.onrender.com")


# Groups the existing Sign Video library (SignVideo table) into a sensible
# Easy -> Medium -> Hard progression for the Sign Match and Typing games,
# instead of relying on an unstructured fallback pool. Words are matched to
# SignVideo rows by their `word` field (case-insensitive); words with no
# matching video are skipped so a missing upload never breaks the migration.
LEVELS = {
    "easy": [
        # Level 1: first half of the alphabet
        ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M"],
        # Level 2: second half of the alphabet
        ["N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"],
    ],
    "medium": [
        # Level 1: greetings
        ["Hello", "Good morning", "Good afternoon", "Good evening", "Goodbye", "Welcome"],
        # Level 2: everyday courtesy expressions + common action words
        ["Please", "Thank you", "You're welcome", "Sorry", "Excuse me",
         "Eat", "Drink", "Sleep", "Work", "Study", "Read", "Write", "Food", "Water"],
    ],
    "hard": [
        # Level 1: emotions + short responses
        ["Happy", "Sad", "Angry", "Afraid", "Excited", "Tired", "Love",
         "Yes", "No", "Maybe", "Again", "Wait", "Help", "I understand", "I don't understand"],
        # Level 2: full conversational phrases
        ["How are you", "I'm fine", "What is your name", "My name is",
         "Nice to meet you", "I need help", "Can you repeat that"],
    ],
}

TITLES = {
    ("easy", 1): "Alphabet: A to M",
    ("easy", 2): "Alphabet: N to Z",
    ("medium", 1): "Greetings",
    ("medium", 2): "Courtesy & Everyday Words",
    ("hard", 1): "Emotions & Responses",
    ("hard", 2): "Conversational Phrases",
}


def _video_url_for(video):
    if not video.video:
        return ""
    try:
        return f"{MEDIA_BASE_URL.rstrip('/')}{video.video.url}"
    except ValueError:
        return ""


def seed_levels(apps, schema_editor):
    GameLevel = apps.get_model("signtext", "GameLevel")
    GameLevelItem = apps.get_model("signtext", "GameLevelItem")
    SignVideo = apps.get_model("signtext", "SignVideo")

    videos_by_word = {sv.word.strip().lower(): sv for sv in SignVideo.objects.all()}

    for game_key in ("sign_match", "typing"):
        for difficulty, level_word_lists in LEVELS.items():
            for level_number, words in enumerate(level_word_lists, start=1):
                level, _ = GameLevel.objects.update_or_create(
                    game_key=game_key,
                    difficulty=difficulty,
                    level_number=level_number,
                    defaults={
                        "title": TITLES.get((difficulty, level_number), ""),
                        "is_published": True,
                    },
                )
                GameLevelItem.objects.filter(level=level).delete()
                order = 0
                for word in words:
                    video = videos_by_word.get(word.strip().lower())
                    if video is None or not video.video:
                        continue
                    GameLevelItem.objects.create(
                        level=level,
                        prompt=word,
                        answer="",
                        media_url=_video_url_for(video),
                        extra_data={},
                        order=order,
                    )
                    order += 1


def remove_levels(apps, schema_editor):
    GameLevel = apps.get_model("signtext", "GameLevel")
    for difficulty, level_word_lists in LEVELS.items():
        for level_number in range(1, len(level_word_lists) + 1):
            GameLevel.objects.filter(
                game_key__in=["sign_match", "typing"],
                difficulty=difficulty,
                level_number=level_number,
            ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("signtext", "0021_seed_certificates"),
    ]

    operations = [
        migrations.RunPython(seed_levels, remove_levels),
    ]
