import os

from django.db import migrations


# Matches the convention in 0019/0023: overridable media host.
MEDIA_BASE_URL = os.getenv("KUMPAS_MEDIA_BASE_URL", "https://kumpass.onrender.com")


# Supersedes 0019_seed_sentence_scenario_levels: instead of one level per
# difficulty holding many items, each item becomes its own single-item level
# (matching Sign Match/Typing's "one level = one round" shape). Only 6
# sentences and 8 scenarios exist today, so counts are lower than the
# Easy/Medium/Hard 5/10/15 target used for Sign Match/Typing -- distributed
# proportionally (roughly 1:2:3) until more content is authored.
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

# 6 sentences -> 1 easy, 2 medium, 3 hard.
SENTENCE_DIFFICULTY_SPLIT = ["easy"] + ["medium"] * 2 + ["hard"] * 3
# 8 scenarios -> 1 easy, 3 medium, 4 hard.
SCENARIO_DIFFICULTY_SPLIT = ["easy"] + ["medium"] * 3 + ["hard"] * 4


def _video_url_for(sign_videos, word):
    obj = sign_videos.get(word.strip().lower())
    if obj is None or not obj.video:
        return ""
    try:
        return f"{MEDIA_BASE_URL.rstrip('/')}{obj.video.url}"
    except ValueError:
        return ""


def reshape_levels(apps, schema_editor):
    GameLevel = apps.get_model("signtext", "GameLevel")
    GameLevelItem = apps.get_model("signtext", "GameLevelItem")
    SignVideo = apps.get_model("signtext", "SignVideo")

    sign_videos = {sv.word.strip().lower(): sv for sv in SignVideo.objects.all()}

    # Drop the old "many items in one level" shape from 0019 entirely.
    GameLevel.objects.filter(game_key__in=["sentence", "scenario"]).delete()

    level_numbers = {"easy": 0, "medium": 0, "hard": 0}
    for item, difficulty in zip(SENTENCE_ITEMS, SENTENCE_DIFFICULTY_SPLIT):
        level_numbers[difficulty] += 1
        signs = [
            {"name": sign["name"], "video": _video_url_for(sign_videos, sign["word"])}
            for sign in item["signs"]
        ]
        sentence_text = " ".join(item["correct"])
        level = GameLevel.objects.create(
            game_key="sentence",
            difficulty=difficulty,
            level_number=level_numbers[difficulty],
            title=sentence_text.title(),
            is_published=True,
        )
        GameLevelItem.objects.create(
            level=level,
            prompt=sentence_text,
            answer=sentence_text,
            media_url="",
            extra_data={"signs": signs, "correct": item["correct"]},
            order=0,
        )

    level_numbers = {"easy": 0, "medium": 0, "hard": 0}
    for item, difficulty in zip(SCENARIO_ITEMS, SCENARIO_DIFFICULTY_SPLIT):
        level_numbers[difficulty] += 1
        options = [
            {
                "name": opt["word"].upper(),
                "video": _video_url_for(sign_videos, opt["word"]),
                "correct": opt["correct"],
            }
            for opt in item["options"]
        ]
        level = GameLevel.objects.create(
            game_key="scenario",
            difficulty=difficulty,
            level_number=level_numbers[difficulty],
            title=item["scenario"][:60],
            is_published=True,
        )
        GameLevelItem.objects.create(
            level=level,
            prompt=item["scenario"],
            answer="",
            media_url="",
            extra_data={"question": item["question"], "options": options},
            order=0,
        )


def remove_levels(apps, schema_editor):
    GameLevel = apps.get_model("signtext", "GameLevel")
    GameLevel.objects.filter(game_key__in=["sentence", "scenario"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("signtext", "0023_reshape_sign_match_typing_levels"),
    ]

    operations = [
        migrations.RunPython(reshape_levels, remove_levels),
    ]
