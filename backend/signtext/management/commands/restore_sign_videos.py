import json
from pathlib import Path

from django.core.management.base import BaseCommand

from signtext.models import SignVideo

# Every SignVideo row the app ships with: the original "Sign Language"
# library (recovered from kumpas_backup.dump) plus the FSL-105 clips. Each
# "video" path points at a file committed under backend/media/, so no
# upload is needed -- the serializers serve it straight from local /media/.
SEED_FILE = Path(__file__).resolve().parents[2] / "data" / "sign_videos_seed.json"


FSL105_PREFIX = "fsl105_"


def _seed_group(key: str) -> str:
    return "fsl105" if key.startswith(FSL105_PREFIX) else "original"


def restore_sign_videos(only_missing_groups: bool = False) -> int:
    """Create any missing SignVideo rows from the seed file.

    Never touches rows that already exist (matched by key), so admin edits
    survive. Returns the number of rows created.

    With only_missing_groups=True (used at startup), a seed group -- the
    original library or the FSL-105 clips -- is restored only when the
    database has no rows from that group at all. That way a database that
    kept the original 68 videos but lost every FSL-105 row still gets the
    FSL-105 words back, while an admin deleting a few individual videos
    doesn't see them reappear on the next restart.
    """
    seed = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    existing = set(SignVideo.objects.values_list("key", flat=True))

    if only_missing_groups:
        present_groups = {_seed_group(key) for key in existing}
        seed = [row for row in seed if _seed_group(row["key"]) not in present_groups]

    missing = [
        SignVideo(
            key=row["key"],
            word=row["word"],
            category=row["category"],
            video=row["video"],
            order=row["order"],
        )
        for row in seed
        if row["key"] not in existing
    ]
    SignVideo.objects.bulk_create(missing)
    return len(missing)


class Command(BaseCommand):
    help = "Re-create missing sign video rows from the bundled seed file (files are already in backend/media/)."

    def handle(self, *args, **options):
        created = restore_sign_videos()
        self.stdout.write(self.style.SUCCESS(f"Restored {created} sign video(s)."))
