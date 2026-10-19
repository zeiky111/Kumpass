import json
from pathlib import Path

from django.core.management.base import BaseCommand

from signtext.models import SignVideo

# Every SignVideo row the app ships with: the original "Sign Language"
# library (recovered from kumpas_backup.dump) plus the FSL-105 clips. Each
# "video" path points at a file committed under backend/media/, so no
# upload is needed -- the serializers serve it straight from local /media/.
SEED_FILE = Path(__file__).resolve().parents[2] / "data" / "sign_videos_seed.json"


def restore_sign_videos(only_if_empty: bool = False) -> int:
    """Create any missing SignVideo rows from the seed file.

    Never touches rows that already exist (matched by key), so admin edits
    survive. Returns the number of rows created.
    """
    if only_if_empty and SignVideo.objects.exists():
        return 0

    seed = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    existing = set(SignVideo.objects.values_list("key", flat=True))
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
