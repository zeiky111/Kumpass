"""Rebuild the default game levels from the SignVideo library.

The default levels for all four games are created by data migrations that
look words up in the SignVideo table. On a fresh database those migrations
run before any sign videos exist, so Sign Match and Typing end up with no
levels at all and Sentence/Scenario rounds have no videos. Re-running the
same migration functions, in their original order, once the videos are back
produces exactly the levels a fully-populated database would have.
"""

from importlib import import_module

from django.apps import apps
from django.db import transaction

# The forward functions that define the current default levels. Earlier
# seeds (0019, 0022) are superseded: 0023 and 0024 delete and recreate
# everything for their games.
SEED_STEPS = [
    ("0023_reshape_sign_match_typing_levels", "reshape_levels"),
    ("0024_reshape_sentence_scenario_levels", "reshape_levels"),
    ("0028_expand_game_level_databank", "expand_databank"),
    ("0032_pool_remaining_sign_videos_into_existing_levels", "pool_remaining_videos"),
]


def rebuild_default_game_levels():
    with transaction.atomic():
        for module_name, func_name in SEED_STEPS:
            module = import_module(f"signtext.migrations.{module_name}")
            getattr(module, func_name)(apps, None)


def rebuild_game_levels_if_missing():
    """Rebuild only when the video-driven games have no levels but videos exist.

    This is the signature of a database that was migrated while empty. It
    never runs once Sign Match or Typing has any level, so teacher-made
    levels are left alone. Returns True if a rebuild happened.
    """
    GameLevel = apps.get_model("signtext", "GameLevel")
    SignVideo = apps.get_model("signtext", "SignVideo")
    if GameLevel.objects.filter(game_key__in=["sign_match", "typing"]).exists():
        return False
    if not SignVideo.objects.exists():
        return False
    rebuild_default_game_levels()
    return True
