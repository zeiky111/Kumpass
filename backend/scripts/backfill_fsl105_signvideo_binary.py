"""One-time backfill: actually upload the SignVideo .mp4 files to Cloudinary.

These files currently only exist on local disk under MEDIA_ROOT (already
committed to git under backend/media/sign_videos/), but every SignVideo.video
field already points to a Cloudinary URL that no file was ever uploaded to --
the DB rows were created without the actual bytes making the trip, so every
video 404s in production (Text-to-Sign and the Games that share this data).

This re-saves each row's `video` field from the local file through Django's
storage API, which -- now that SignVideo.video correctly uses
VideoMediaCloudinaryStorage (see models.py) -- performs a real upload to
Cloudinary under the video resource type instead of just recording a path
that was never backed by an uploaded asset.

Some rows (the fsl105_ prefixed ones imported on 2026/09/02) have a random
suffix in their recorded filename (e.g. "fsl105_april_qpiwLrj.mp4") that
doesn't match the actual local file ("fsl105_april.mp4") -- that suffix was
added by a prior, never-completed save attempt. This script falls back to
matching by filename with that suffix stripped when the exact name isn't
found on disk.

Usage, from the backend/ directory with the main venv active and
CLOUDINARY_URL set (e.g. Render's Shell tab, which already has it):
    python scripts/backfill_fsl105_signvideo_binary.py
"""

from __future__ import annotations

import os
import re
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

from signtext.models import SignVideo  # noqa: E402

# Django's Storage.get_available_name() appends "_" + 7 URL-safe characters
# when a save collides with an existing name -- strip that to recover the
# original filename when the exact recorded name isn't found on disk.
RANDOM_SUFFIX_RE = re.compile(r"^(?P<stem>.+)_[A-Za-z0-9_-]{7}(?P<ext>\.[^.]+)$")


def _strip_suffix(filename: str) -> str:
    match = RANDOM_SUFFIX_RE.match(filename)
    return f"{match.group('stem')}{match.group('ext')}" if match else filename


def build_local_index(media_root: Path) -> dict[str, Path]:
    """Map every local sign_videos file by its own path relative to
    media_root AND by its filename (suffix-stripped) so a lookup works
    regardless of whether the DB's recorded name includes a "media/"
    prefix, a stale random suffix, or both -- we don't have a way to
    inspect the actual production value of SignVideo.video.name from here,
    so match on whatever signal we can rather than assume one convention.
    """
    index: dict[str, Path] = {}
    sign_videos_root = media_root / "sign_videos"
    if not sign_videos_root.is_dir():
        return index

    for path in sign_videos_root.rglob("*.mp4"):
        rel = path.relative_to(media_root).as_posix()
        index.setdefault(rel, path)
        index.setdefault(_strip_suffix(path.name), path)
    return index


def find_local_file(index: dict[str, Path], video_name: str) -> Path | None:
    candidates = [
        video_name,
        video_name.removeprefix("media/"),
        Path(video_name).name,
        _strip_suffix(Path(video_name).name),
    ]
    for candidate in candidates:
        if candidate in index:
            return index[candidate]
    return None


def main() -> None:
    if not getattr(settings, "CLOUDINARY_URL", ""):
        print("CLOUDINARY_URL is not set in this environment -- aborting so "
              "nothing gets (re-)saved to local disk by mistake. Run this "
              "where Cloudinary is actually configured (e.g. Render's Shell).")
        sys.exit(1)

    media_root = Path(settings.MEDIA_ROOT)
    local_index = build_local_index(media_root)
    print(f"Indexed {len(local_index)} local filename variants under {media_root / 'sign_videos'}")

    videos = SignVideo.objects.exclude(video="")
    print(f"Found {videos.count()} SignVideo rows with a file reference")

    uploaded = 0
    missing_file = []

    for video in videos:
        local_path = find_local_file(local_index, video.video.name)
        if local_path is None:
            missing_file.append(video.key)
            print(f"  [skip] {video.key}: no local file for {video.video.name}")
            continue

        content = local_path.read_bytes()
        # save=True writes through SignVideo.video's storage (Cloudinary,
        # resource_type=video) and updates video.name to whatever public_id
        # Cloudinary assigns -- this is the actual upload step that never
        # happened when these rows were first created.
        video.video.save(local_path.name, ContentFile(content), save=True)
        uploaded += 1
        print(f"  [ok] {video.key}: uploaded {len(content)} bytes from {local_path.name}")

    print(f"\nDone. Uploaded {uploaded}, missing local file for {len(missing_file)}.")
    if missing_file:
        print("Missing file for:", missing_file)


if __name__ == "__main__":
    main()
