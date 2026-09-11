"""One-time backfill: re-save every SignVideo.video file through the
current default storage (Cloudinary when CLOUDINARY_URL is configured),
so videos survive Render's ephemeral disk instead of 404ing after the
next deploy/restart.

Must be run in an environment where CLOUDINARY_URL is set (i.e. on Render,
via `render run` or the shell tab) -- running it locally just re-saves
files back to local disk and accomplishes nothing.

Usage, from the backend/ directory with the venv active:
    python scripts/backfill_signvideo_to_cloudinary.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kumpas_api.settings")
import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.core.files.base import ContentFile  # noqa: E402
from django.core.files.storage import FileSystemStorage  # noqa: E402
from signtext.models import SignVideo  # noqa: E402


def main() -> None:
    if not getattr(settings, "CLOUDINARY_URL", ""):
        print("CLOUDINARY_URL is not set in this environment -- aborting. "
              "Run this on Render (where Cloudinary is configured), not locally.")
        return

    # SignVideo.video now resolves to Cloudinary storage in this environment,
    # so we read the old bytes directly off local disk (MEDIA_ROOT) rather
    # than through the field's (already-Cloudinary) storage object.
    local_storage = FileSystemStorage(location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)

    videos = SignVideo.objects.exclude(video="")
    print(f"Found {videos.count()} SignVideo rows with a file reference")

    updated = 0
    already_on_cloudinary = 0
    missing = []

    for video in videos:
        try:
            cloudinary_exists = video.video.storage.exists(video.video.name)
        except Exception:
            cloudinary_exists = False
        if cloudinary_exists:
            already_on_cloudinary += 1
            continue

        if not local_storage.exists(video.video.name):
            print(f"  [skip] {video.key}: local file not found ({video.video.name})")
            missing.append(video.key)
            continue

        with local_storage.open(video.video.name, "rb") as fh:
            data = fh.read()

        filename = Path(video.video.name).name
        video.video.save(filename, ContentFile(data), save=True)
        updated += 1
        print(f"  [ok] {video.key}: uploaded {len(data)} bytes to Cloudinary")

    print(f"\nDone. Uploaded {updated}, already on Cloudinary {already_on_cloudinary}, missing locally {len(missing)}.")
    if missing:
        print("Missing local file for:", missing)


if __name__ == "__main__":
    main()
