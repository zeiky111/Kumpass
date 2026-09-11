import os

from django.db import migrations


# Expands the Games databank so each difficulty has enough levels that a
# session doesn't exhaust a difficulty after 1-5 questions (see 0023/0024's
# own comments noting content was under target). This migration APPENDS new
# GameLevel rows after the current max level_number per game+difficulty --
# it does not touch or delete any existing level, so previously-authored
# content (and any instructor edits made to it) is left alone.
#
# Target level counts per difficulty: easy=8, medium=10, hard=12.
# Video content is drawn from the SignVideo table, which now includes the
# FSL-105 dataset words (see scripts/transcode_fsl105_to_signvideo.py) in
# addition to the original hand-uploaded library.
MEDIA_BASE_URL = os.getenv("KUMPAS_MEDIA_BASE_URL", "https://kumpass.onrender.com")

TARGET_COUNTS = {"easy": 8, "medium": 10, "hard": 12}

# ---- Sign Match / Typing: additional words, one per new level ----
# Easy continues the existing alphabet progression (A-E already exist).
NEW_WORDS = {
    "easy": ["F", "G", "H"],
    "medium": [],  # already at target (10)
    "hard": [],  # already at/above target (15)
}

# ---- Sentence Builder: additional sentences, 2-5 signs each ----
NEW_SENTENCES = {
    "easy": [
        {"signs": ["hello", "good morning"], "correct": ["hello", "good", "morning"]},
        {"signs": ["please", "help"], "correct": ["please", "help"]},
        {"signs": ["thank you", "goodbye"], "correct": ["thank", "you", "goodbye"]},
        {"signs": ["sorry", "excuse me"], "correct": ["sorry", "excuse", "me"]},
        {"signs": ["yes", "please"], "correct": ["yes", "please"]},
        {"signs": ["no", "thank you"], "correct": ["no", "thank", "you"]},
        {"signs": ["good afternoon", "father"], "correct": ["good", "afternoon", "father"]},
    ],
    "medium": [
        {"signs": ["good morning", "how are you"], "correct": ["good", "morning", "how", "are", "you"]},
        {"signs": ["i understand", "thank you"], "correct": ["i", "understand", "thank", "you"]},
        {"signs": ["i don't understand", "can you repeat that"],
         "correct": ["i", "don't", "understand", "can", "you", "repeat", "that"]},
        {"signs": ["what is your name", "nice to meet you"],
         "correct": ["what", "is", "your", "name", "nice", "to", "meet", "you"]},
        {"signs": ["i need help", "please"], "correct": ["i", "need", "help", "please"]},
        {"signs": ["mother", "father"], "correct": ["mother", "and", "father"]},
        {"signs": ["red", "blue", "yellow"], "correct": ["red", "blue", "yellow"]},
        {"signs": ["one", "two", "three"], "correct": ["one", "two", "three"]},
    ],
    "hard": [
        {"signs": ["good evening", "how are you", "i'm fine"],
         "correct": ["good", "evening", "how", "are", "you", "i'm", "fine"]},
        {"signs": ["hello", "my name is", "nice to meet you"],
         "correct": ["hello", "my", "name", "is", "nice", "to", "meet", "you"]},
        {"signs": ["excuse me", "i need help", "thank you"],
         "correct": ["excuse", "me", "i", "need", "help", "thank", "you"]},
        {"signs": ["what is your name", "i'm fine", "nice to meet you"],
         "correct": ["what", "is", "your", "name", "nice", "to", "meet", "you"]},
        {"signs": ["today", "tomorrow", "yesterday"], "correct": ["today", "tomorrow", "yesterday"]},
        {"signs": ["fsl105_grandmother", "fsl105_grandfather"], "correct": ["grandmother", "and", "grandfather"]},
        {"signs": ["hot", "coffee", "please"], "correct": ["hot", "coffee", "please"]},
        {"signs": ["cold", "water", "please"], "correct": ["cold", "water", "please"]},
        {"signs": ["monday", "tuesday", "wednesday"], "correct": ["monday", "tuesday", "wednesday"]},
    ],
}

# ---- Scenario-Based: additional scenarios, one correct sign + 2 decoys ----
NEW_SCENARIOS = {
    "easy": [
        {
            "scenario": "You want a glass of water because you are thirsty.",
            "question": "Which sign shows what you want?",
            "options": [{"word": "water", "correct": True}, {"word": "food", "correct": False},
                        {"word": "sleep", "correct": False}],
        },
        {
            "scenario": "It is morning and you see your teacher for the first time today.",
            "question": "Which greeting fits best?",
            "options": [{"word": "good morning", "correct": True}, {"word": "good evening", "correct": False},
                        {"word": "goodbye", "correct": False}],
        },
        {
            "scenario": "Someone offers you food, but you already ate.",
            "question": "How do you politely respond?",
            "options": [{"word": "no", "correct": True}, {"word": "yes", "correct": False},
                        {"word": "help", "correct": False}],
        },
        {
            "scenario": "You need someone's help to carry your bag.",
            "question": "Which sign do you use to ask?",
            "options": [{"word": "help", "correct": True}, {"word": "wait", "correct": False},
                        {"word": "sorry", "correct": False}],
        },
        {
            "scenario": "Your friend asks if you are hungry, and you are.",
            "question": "How do you answer?",
            "options": [{"word": "yes", "correct": True}, {"word": "no", "correct": False},
                        {"word": "maybe", "correct": False}],
        },
        {
            "scenario": "You want your friend to wait a moment before leaving.",
            "question": "Which sign do you show?",
            "options": [{"word": "wait", "correct": True}, {"word": "again", "correct": False},
                        {"word": "goodbye", "correct": False}],
        },
        {
            "scenario": "You are introducing your mother to a classmate.",
            "question": "Which sign refers to her?",
            "options": [{"word": "fsl105_mother", "correct": True}, {"word": "fsl105_father", "correct": False},
                        {"word": "fsl105_son", "correct": False}],
        },
    ],
    "medium": [
        {
            "scenario": "You are ordering a cold drink at a canteen.",
            "question": "Which sign tells them what you want?",
            "options": [{"word": "fsl105_cold", "correct": True}, {"word": "fsl105_hot", "correct": False},
                        {"word": "fsl105_sugar", "correct": False}, {"word": "fsl105_juice", "correct": False}],
        },
        {
            "scenario": "A classmate did not hear what you said clearly.",
            "question": "Which sign do you show to ask them to repeat?",
            "options": [{"word": "can you repeat that", "correct": True}, {"word": "excuse me", "correct": False},
                        {"word": "sorry", "correct": False}, {"word": "wait", "correct": False}],
        },
        {
            "scenario": "You just met someone and want to know their name.",
            "question": "Which sign do you use?",
            "options": [{"word": "what is your name", "correct": True}, {"word": "how are you", "correct": False},
                        {"word": "nice to meet you", "correct": False}, {"word": "hello", "correct": False}],
        },
        {
            "scenario": "You are asked what color your shirt is, and it is red.",
            "question": "Which sign answers correctly?",
            "options": [{"word": "fsl105_red", "correct": True}, {"word": "fsl105_blue", "correct": False},
                        {"word": "fsl105_green", "correct": False}, {"word": "fsl105_yellow", "correct": False}],
        },
        {
            "scenario": "Someone asks how many siblings you have, and the answer is three.",
            "question": "Which sign gives the correct number?",
            "options": [{"word": "fsl105_three", "correct": True}, {"word": "fsl105_two", "correct": False},
                        {"word": "fsl105_four", "correct": False}, {"word": "fsl105_five", "correct": False}],
        },
        {
            "scenario": "You are talking about your family and want to mention your father.",
            "question": "Which sign refers to him?",
            "options": [{"word": "fsl105_father", "correct": True}, {"word": "fsl105_uncle", "correct": False},
                        {"word": "fsl105_grandfather", "correct": False}, {"word": "fsl105_son", "correct": False}],
        },
        {
            "scenario": "Your teacher explains something and you fully understand it.",
            "question": "Which sign do you show?",
            "options": [{"word": "i understand", "correct": True}, {"word": "i don't understand", "correct": False},
                        {"word": "maybe", "correct": False}, {"word": "wait", "correct": False}],
        },
    ],
    "hard": [
        {
            "scenario": "A classmate explains a lesson twice, but you still don't get it.",
            "question": "",
            "options": [{"word": "i don't understand", "correct": True}, {"word": "i understand", "correct": False},
                        {"word": "fsl105_wrong", "correct": False}, {"word": "fsl105_correct", "correct": False}],
        },
        {
            "scenario": "You are asked to confirm if an answer on the board is right, and it is.",
            "question": "",
            "options": [{"word": "fsl105_correct", "correct": True}, {"word": "fsl105_wrong", "correct": False},
                        {"word": "fsl105_know", "correct": False}, {"word": "yes", "correct": False}],
        },
        {
            "scenario": "You need to describe someone who cannot hear at all.",
            "question": "",
            "options": [{"word": "fsl105_deaf", "correct": True}, {"word": "fsl105_blind", "correct": False},
                        {"word": "fsl105_hard_of_hearing", "correct": False},
                        {"word": "fsl105_deaf_blind", "correct": False}],
        },
        {
            "scenario": "Someone can hear a little but not everything clearly.",
            "question": "",
            "options": [{"word": "fsl105_hard_of_hearing", "correct": True}, {"word": "fsl105_deaf", "correct": False},
                        {"word": "fsl105_blind", "correct": False}, {"word": "fsl105_slow", "correct": False}],
        },
        {
            "scenario": "You want to say you already know the answer before it's explained.",
            "question": "",
            "options": [{"word": "fsl105_know", "correct": True}, {"word": "fsl105_don_t_know", "correct": False},
                        {"word": "maybe", "correct": False}, {"word": "i understand", "correct": False}],
        },
        {
            "scenario": "You are asked what day tomorrow is, and today is Monday.",
            "question": "",
            "options": [{"word": "fsl105_tuesday", "correct": True}, {"word": "fsl105_sunday", "correct": False},
                        {"word": "fsl105_wednesday", "correct": False}, {"word": "fsl105_monday", "correct": False}],
        },
        {
            "scenario": "You need to sign that someone is married during a conversation about family.",
            "question": "",
            "options": [{"word": "fsl105_married", "correct": True}, {"word": "fsl105_parents", "correct": False},
                        {"word": "fsl105_woman", "correct": False}, {"word": "fsl105_man", "correct": False}],
        },
        {
            "scenario": "A teammate is signing too fast for you to follow.",
            "question": "",
            "options": [{"word": "fsl105_slow", "correct": True}, {"word": "fsl105_fast", "correct": False},
                        {"word": "wait", "correct": False}, {"word": "again", "correct": False}],
        },
    ],
}


def _video_url_for(sign_videos, word):
    key = word.strip().lower()
    obj = sign_videos.get(key)
    if obj is None or not obj.video:
        return ""
    try:
        return f"{MEDIA_BASE_URL.rstrip('/')}{obj.video.url}"
    except ValueError:
        return ""


def _lookup_table(SignVideo):
    # Index by both `word` (lowercased) and `key`, so scenario/sentence data
    # above can reference either a plain word ("water") or an explicit
    # SignVideo key ("fsl105_mother") when disambiguation is needed.
    table = {}
    for sv in SignVideo.objects.all():
        table[sv.word.strip().lower()] = sv
        table[sv.key.strip().lower()] = sv
    return table


def expand_databank(apps, schema_editor):
    GameLevel = apps.get_model("signtext", "GameLevel")
    GameLevelItem = apps.get_model("signtext", "GameLevelItem")
    SignVideo = apps.get_model("signtext", "SignVideo")

    sign_videos = _lookup_table(SignVideo)

    # --- Sign Match / Typing ---
    for game_key in ("sign_match", "typing"):
        for difficulty, words in NEW_WORDS.items():
            if not words:
                continue
            start = (
                GameLevel.objects.filter(game_key=game_key, difficulty=difficulty)
                .order_by("-level_number")
                .values_list("level_number", flat=True)
                .first()
                or 0
            )
            for offset, word in enumerate(words, start=1):
                video = sign_videos.get(word.strip().lower())
                if video is None or not video.video:
                    continue
                level = GameLevel.objects.create(
                    game_key=game_key,
                    difficulty=difficulty,
                    level_number=start + offset,
                    title=word,
                    is_published=True,
                )
                GameLevelItem.objects.create(
                    level=level,
                    prompt=word,
                    answer="",
                    media_url=_video_url_for(sign_videos, word),
                    extra_data={},
                    order=0,
                )

    # --- Sentence Builder ---
    for difficulty, sentences in NEW_SENTENCES.items():
        start = (
            GameLevel.objects.filter(game_key="sentence", difficulty=difficulty)
            .order_by("-level_number")
            .values_list("level_number", flat=True)
            .first()
            or 0
        )
        for offset, item in enumerate(sentences, start=1):
            signs = [
                {"name": w.upper(), "video": _video_url_for(sign_videos, w)}
                for w in item["signs"]
            ]
            sentence_text = " ".join(item["correct"])
            level = GameLevel.objects.create(
                game_key="sentence",
                difficulty=difficulty,
                level_number=start + offset,
                title=sentence_text.title()[:60],
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

    # --- Scenario-Based ---
    for difficulty, scenarios in NEW_SCENARIOS.items():
        start = (
            GameLevel.objects.filter(game_key="scenario", difficulty=difficulty)
            .order_by("-level_number")
            .values_list("level_number", flat=True)
            .first()
            or 0
        )
        for offset, item in enumerate(scenarios, start=1):
            options = [
                {
                    "name": sign_videos[opt["word"].strip().lower()].word.upper()
                    if opt["word"].strip().lower() in sign_videos else opt["word"].upper(),
                    "video": _video_url_for(sign_videos, opt["word"]),
                    "correct": opt["correct"],
                }
                for opt in item["options"]
            ]
            level = GameLevel.objects.create(
                game_key="scenario",
                difficulty=difficulty,
                level_number=start + offset,
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


def remove_expansion(apps, schema_editor):
    GameLevel = apps.get_model("signtext", "GameLevel")

    for difficulty, words in NEW_WORDS.items():
        if not words:
            continue
        # These were appended after the pre-existing max, so their
        # level_numbers are the highest N for their game+difficulty.
        for game_key in ("sign_match", "typing"):
            existing = GameLevel.objects.filter(game_key=game_key, difficulty=difficulty)
            total = existing.count()
            if total >= len(words):
                cutoff = total - len(words)
                nums_to_delete = list(
                    existing.order_by("level_number").values_list("level_number", flat=True)
                )[cutoff:]
                existing.filter(level_number__in=nums_to_delete).delete()

    for difficulty, sentences in NEW_SENTENCES.items():
        existing = GameLevel.objects.filter(game_key="sentence", difficulty=difficulty)
        total = existing.count()
        if total >= len(sentences):
            cutoff = total - len(sentences)
            nums_to_delete = list(
                existing.order_by("level_number").values_list("level_number", flat=True)
            )[cutoff:]
            existing.filter(level_number__in=nums_to_delete).delete()

    for difficulty, scenarios in NEW_SCENARIOS.items():
        existing = GameLevel.objects.filter(game_key="scenario", difficulty=difficulty)
        total = existing.count()
        if total >= len(scenarios):
            cutoff = total - len(scenarios)
            nums_to_delete = list(
                existing.order_by("level_number").values_list("level_number", flat=True)
            )[cutoff:]
            existing.filter(level_number__in=nums_to_delete).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("signtext", "0027_extend_signvideo_categories"),
    ]

    operations = [
        migrations.RunPython(expand_databank, remove_expansion),
    ]
