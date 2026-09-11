"""One-time backfill: copy the already-transcoded FSL-105 SignVideo .mp4
files (currently only sitting on local disk under MEDIA_ROOT, which never
reached production/Cloudinary) into the new video_data binary column, so
playback no longer depends on that file existing anywhere.

Usage, from the backend/ directory with the main venv active:
    python scripts/backfill_fsl105_signvideo_binary.py
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

from signtext.models import SignVideo  # noqa: E402


def main() -> None:
    videos = SignVideo.objects.filter(key__startswith="fsl105_").exclude(video="")
    print(f"Found {videos.count()} fsl105_ SignVideo rows with a file reference")

    updated = 0
    missing_file = []
    already_had_data = 0

    for video in videos:
        if video.video_data:
            already_had_data += 1
            continue

        file_path = Path(video.video.path)
        if not file_path.exists():
            missing_file.append(video.key)
            print(f"  [skip] {video.key}: file not found at {file_path}")
            continue

        video.video_data = file_path.read_bytes()
        video.video_content_type = "video/mp4"
        video.video_filename = f"{video.key}.mp4"
        video.save(update_fields=["video_data", "video_content_type", "video_filename"])
        updated += 1
        print(f"  [ok] {video.key}: {len(video.video_data)} bytes")

    print(
        f"\nDone. Updated {updated}, already had data {already_had_data}, "
        f"missing file {len(missing_file)}."
    )
    if missing_file:
        print("Missing file for:", missing_file)


if __name__ == "__main__":
    main()
