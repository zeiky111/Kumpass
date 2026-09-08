import os

from django.db import migrations


# Puts every remaining unused SignVideo (79 words: alphabet I-Z, colors,
# days, drinks, everyday words, numbers, calendar months, family, food,
# relationships, and a few leftover greetings/survival words) into play
# WITHOUT changing how many levels exist per difficulty per game. Each
# existing GameLevel keeps its own level_number/title/item count -- the
# extra words are attached as extra_data.pool alternatives on the existing
# GameLevelItem, so games-common.js's buildQuestionsForCurrentLevel() can
# redraw a different word for that same level slot on each playthrough
# (see js/games-common.js: buildLevelsByDifficulty's `_pool` / drawFromPool).
MEDIA_BASE_URL = os.getenv("KUMPAS_MEDIA_BASE_URL", "https://kumpass.onrender.com")

# Extra words distributed across the EXISTING Sign Match/Typing levels for
# each difficulty (spread roughly evenly across however many levels already
# exist there -- 8 easy, 10 medium, 15 hard).
EXTRA_WORDS = {
    "easy": ["I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"],
    "medium": [
        "Black", "Brown", "Dark", "Gray", "Light", "Orange", "Pink", "Violet", "White",
        "Friday", "Saturday", "Thursday",
        "Drink", "Eat", "Read", "Study", "Work", "Write",
    ],
    "hard": [
        "Eight", "Nine", "Seven", "Six", "Ten",
        "April", "August", "December", "February", "January", "July", "June", "March", "May",
        "November", "October", "September",
        "Auntie", "Cousin", "Daughter", "Grandmother",
        "Bread", "Chicken", "Crab", "Egg", "Fish", "Longanisa", "Meat", "Rice", "Shrimp", "Spaghetti",
        "Beer", "Milk", "No Sugar", "Tea", "Wine",
        "Boy", "Girl", "Weelchair Person",
        "Understand",
        "Im Fine", "See You Tomorrow",
        "You're welcome",
    ],
}


def _video_url_for(sign_videos, word):
    obj = sign_videos.get(word.strip().lower())
    if obj is None or not obj.video:
        return ""
    try:
        return f"{MEDIA_BASE_URL.rstrip('/')}{obj.video.url}"
    except ValueError:
        return ""


def _distribute(words, bucket_count):
    """Splits `words` into `bucket_count` roughly-even lists, in order."""
    buckets = [[] for _ in range(bucket_count)]
    for i, word in enumerate(words):
        buckets[i % bucket_count].append(word)
    return buckets


def pool_remaining_videos(apps, schema_editor):
    GameLevel = apps.get_model("signtext", "GameLevel")
    SignVideo = apps.get_model("signtext", "SignVideo")

    sign_videos = {sv.word.strip().lower(): sv for sv in SignVideo.objects.all()}

    for game_key in ("sign_match", "typing"):
        for difficulty, words in EXTRA_WORDS.items():
            levels = list(
                GameLevel.objects.filter(game_key=game_key, difficulty=difficulty).order_by("level_number")
            )
            if not levels:
                continue
            buckets = _distribute(words, len(levels))
            for level, bucket in zip(levels, buckets):
                item = level.items.first()
                if item is None or not bucket:
                    continue
                pool_entries = []
                for word in bucket:
                    video = sign_videos.get(word.strip().lower())
                    if video is None or not video.video:
                        continue
                    pool_entries.append({
                        "prompt": word,
                        "media_url": _video_url_for(sign_videos, word),
                        "extra_data": {},
                    })
                if not pool_entries:
                    continue
                extra = dict(item.extra_data or {})
                extra["pool"] = pool_entries
                item.extra_data = extra
                item.save()


def remove_pools(apps, schema_editor):
    GameLevel = apps.get_model("signtext", "GameLevel")

    for game_key in ("sign_match", "typing"):
        for difficulty in EXTRA_WORDS:
            for level in GameLevel.objects.filter(game_key=game_key, difficulty=difficulty):
                item = level.items.first()
                if item is None:
                    continue
                extra = dict(item.extra_data or {})
                if "pool" in extra:
                    del extra["pool"]
                    item.extra_data = extra
                    item.save()


class Migration(migrations.Migration):

    dependencies = [
        ("signtext", "0031_remove_signvideo_video_content_type_and_more"),
    ]

    operations = [
        migrations.RunPython(pool_remaining_videos, remove_pools),
    ]
