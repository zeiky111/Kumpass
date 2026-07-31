import os

from django.db import migrations


# Matches the frontend's own hardcoded fallback backend origin (see e.g.
# js/games-common.js: `localStorage.getItem('kumpasApiBase') || 'https://kumpass.onrender.com/api'`).
# Overridable via env for other deployments.
MEDIA_BASE_URL = os.getenv("KUMPAS_MEDIA_BASE_URL", "https://kumpass.onrender.com")

SENTENCE_ITEMS = [
    {
        "signs": [
            {"name": "HELLO", "word": "hello"},
            {"name": "HOW ARE YOU", "word": "how are you"},
        ],
        "correct": ["hello", "how", "are", "you"],
    },
    {
        "signs": [
            {"name": "HELLO", "word": "hello"},
            {"name": "WHAT IS YOUR NAME", "word": "what is your name"},
        ],
        "correct": ["hello", "what", "is", "your", "name"],
    },
    {
        "signs": [
            {"name": "MY NAME IS", "word": "my name is"},
            {"name": "NICE TO MEET YOU", "word": "nice to meet you"},
        ],
        "correct": ["my", "name", "is", "nice", "to", "meet", "you"],
    },
    {
        "signs": [
            {"name": "I NEED HELP", "word": "i need help"},
            {"name": "THANK YOU", "word": "thank you"},
        ],
        "correct": ["i", "need", "help", "thank", "you"],
    },
    {
        "signs": [
            {"name": "EXCUSE ME", "word": "excuse me"},
            {"name": "CAN YOU REPEAT THAT", "word": "can you repeat that"},
        ],
        "correct": ["excuse", "me", "can", "you", "repeat", "that"],
    },
    {
        "signs": [
            {"name": "THANK YOU", "word": "thank you"},
            {"name": "GOODBYE", "word": "goodbye"},
        ],
        "correct": ["thank", "you", "goodbye"],
    },
]

SCENARIO_ITEMS = [
    {
        "scenario": "You bump into someone in the hallway and need to apologize.",
        "question": "Which sign response should you use?",
        "options": [
            {"word": "sorry", "correct": True},
            {"word": "thank you", "correct": False},
            {"word": "hello", "correct": False},
        ],
    },
    {
        "scenario": "You start a conversation with someone new in class.",
        "question": "What is your best opening sign?",
        "options": [
            {"word": "hello", "correct": True},
            {"word": "goodbye", "correct": False},
            {"word": "sorry", "correct": False},
        ],
    },
    {
        "scenario": "You want to ask someone how they are feeling today.",
        "question": "Pick the most appropriate sign question:",
        "options": [
            {"word": "how are you", "correct": True},
            {"word": "what is your name", "correct": False},
            {"word": "please", "correct": False},
        ],
    },
    {
        "scenario": "You want to know the name of a new classmate.",
        "question": "Which sign should you use to ask?",
        "options": [
            {"word": "what is your name", "correct": True},
            {"word": "how are you", "correct": False},
            {"word": "nice to meet you", "correct": False},
        ],
    },
    {
        "scenario": "Someone just told you their name and you want to respond politely.",
        "question": "Which sign fits best?",
        "options": [
            {"word": "nice to meet you", "correct": True},
            {"word": "excuse me", "correct": False},
            {"word": "please", "correct": False},
        ],
    },
    {
        "scenario": "A classmate helped you understand a lesson and you want to show appreciation.",
        "question": "Which sign response should you use?",
        "options": [
            {"word": "thank you", "correct": True},
            {"word": "sorry", "correct": False},
            {"word": "hello", "correct": False},
        ],
    },
    {
        "scenario": "You need to pass by someone blocking the hallway.",
        "question": "Which sign should you show first?",
        "options": [
            {"word": "excuse me", "correct": True},
            {"word": "please", "correct": False},
            {"word": "sorry", "correct": False},
        ],
    },
    {
        "scenario": "It is the end of the school day and you are leaving.",
        "question": "Which sign fits this situation?",
        "options": [
            {"word": "goodbye", "correct": True},
            {"word": "hello", "correct": False},
            {"word": "thank you", "correct": False},
        ],
    },
]


def _video_url_for(sign_videos, word):
    obj = sign_videos.get(word.strip().lower())
    if obj is None or not obj.video:
        return ""
    try:
        return f"{MEDIA_BASE_URL.rstrip('/')}{obj.video.url}"
    except ValueError:
        return ""


def seed_levels(apps, schema_editor):
    GameLevel = apps.get_model("signtext", "GameLevel")
    GameLevelItem = apps.get_model("signtext", "GameLevelItem")
    SignVideo = apps.get_model("signtext", "SignVideo")

    sign_videos = {sv.word.strip().lower(): sv for sv in SignVideo.objects.all()}

    sentence_level, _ = GameLevel.objects.update_or_create(
        game_key="sentence",
        difficulty="easy",
        level_number=1,
        defaults={"title": "Everyday Greetings", "is_published": True},
    )
    GameLevelItem.objects.filter(level=sentence_level).delete()
    for order, item in enumerate(SENTENCE_ITEMS):
        signs = [
            {"name": sign["name"], "video": _video_url_for(sign_videos, sign["word"])}
            for sign in item["signs"]
        ]
        sentence_text = " ".join(item["correct"])
        GameLevelItem.objects.create(
            level=sentence_level,
            prompt=sentence_text,
            answer=sentence_text,
            media_url="",
            extra_data={"signs": signs, "correct": item["correct"]},
            order=order,
        )

    scenario_level, _ = GameLevel.objects.update_or_create(
        game_key="scenario",
        difficulty="easy",
        level_number=1,
        defaults={"title": "Common Situations", "is_published": True},
    )
    GameLevelItem.objects.filter(level=scenario_level).delete()
    for order, item in enumerate(SCENARIO_ITEMS):
        options = [
            {
                "name": opt["word"].upper(),
                "video": _video_url_for(sign_videos, opt["word"]),
                "correct": opt["correct"],
            }
            for opt in item["options"]
        ]
        GameLevelItem.objects.create(
            level=scenario_level,
            prompt=item["scenario"],
            answer="",
            media_url="",
            extra_data={"question": item["question"], "options": options},
            order=order,
        )


def remove_levels(apps, schema_editor):
    GameLevel = apps.get_model("signtext", "GameLevel")
    GameLevel.objects.filter(
        game_key__in=["sentence", "scenario"], difficulty="easy", level_number=1
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("signtext", "0018_seed_achievements"),
    ]

    operations = [
        migrations.RunPython(seed_levels, remove_levels),
    ]
