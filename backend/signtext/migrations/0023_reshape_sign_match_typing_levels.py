from django.db import migrations


# Supersedes 0022_seed_sign_match_typing_levels: each level now holds exactly
# ONE word/item (matching the other games' "one level = one round" shape),
# instead of grouping many words into 2 big levels per difficulty. Level
# counts: Easy=5, Medium=10, Hard=15 levels, per game.
LEVELS = {
    "easy": ["A", "B", "C", "D", "E"],
    "medium": [
        "Hello", "Good morning", "Good afternoon", "Good evening", "Goodbye",
        "Welcome", "Please", "Thank you", "Sorry", "Excuse me",
    ],
    "hard": [
        "Happy", "Sad", "Angry", "Afraid", "Excited", "Tired", "Love",
        "How are you", "I'm fine", "What is your name", "My name is",
        "Nice to meet you", "I need help", "Can you repeat that", "Yes",
    ],
}


def _video_url_for(video, media_base_url):
    if not video.video:
        return ""
    try:
        return f"{media_base_url.rstrip('/')}{video.video.url}"
    except ValueError:
        return ""


def reshape_levels(apps, schema_editor):
    import os

    media_base_url = os.getenv("KUMPAS_MEDIA_BASE_URL", "https://kumpass.onrender.com")

    GameLevel = apps.get_model("signtext", "GameLevel")
    GameLevelItem = apps.get_model("signtext", "GameLevelItem")
    SignVideo = apps.get_model("signtext", "SignVideo")

    videos_by_word = {sv.word.strip().lower(): sv for sv in SignVideo.objects.all()}

    for game_key in ("sign_match", "typing"):
        # Remove the old 2-levels-per-difficulty shape from 0022 entirely.
        GameLevel.objects.filter(game_key=game_key).delete()

        for difficulty, words in LEVELS.items():
            for level_number, word in enumerate(words, start=1):
                video = videos_by_word.get(word.strip().lower())
                if video is None or not video.video:
                    continue
                level = GameLevel.objects.create(
                    game_key=game_key,
                    difficulty=difficulty,
                    level_number=level_number,
                    title=word,
                    is_published=True,
                )
                GameLevelItem.objects.create(
                    level=level,
                    prompt=word,
                    answer="",
                    media_url=_video_url_for(video, media_base_url),
                    extra_data={},
                    order=0,
                )


def remove_levels(apps, schema_editor):
    GameLevel = apps.get_model("signtext", "GameLevel")
    GameLevel.objects.filter(game_key__in=["sign_match", "typing"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("signtext", "0022_seed_sign_match_typing_levels"),
    ]

    operations = [
        migrations.RunPython(reshape_levels, remove_levels),
    ]
