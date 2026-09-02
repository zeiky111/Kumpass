"""Transcode one representative clip per FSL-105 word into a browser-playable
SignVideo row, so the Games module can use the FSL-105 dataset's vocabulary
(105 words across 10 categories) instead of being limited to the smaller
hand-uploaded SignVideo library.

Why this exists: FSL105Clip.video_data stores raw .MOV (QuickTime/H.264-in-mov
container) bytes directly in the database (see models.py / import_fsl105.py).
Non-Safari browsers generally can't play that container reliably, which is
why the original SignVideo library keeps separately re-encoded .mp4 files.
This script does the same re-encode for FSL-105: for each distinct label, it
picks one clip, decodes video_data to a temp file, re-encodes it to H.264/AAC
.mp4 via ffmpeg (bundled by the imageio-ffmpeg package -- no system ffmpeg
install required), and saves the result as a SignVideo row so it flows
through the exact same /sign-videos/?scope=games pool the 4 games already
read from. Idempotent: re-running updates existing rows by key instead of
duplicating them.

Usage, from the backend/ directory with the main venv active:
    python scripts/transcode_fsl105_to_signvideo.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kumpas_api.settings")
import django  # noqa: E402

django.setup()

from django.core.files.base import ContentFile  # noqa: E402
from signtext.models import FSL105Clip, SignVideo  # noqa: E402

import imageio_ffmpeg  # noqa: E402

# FSL-105 labels.csv categories -> SignVideo.CATEGORY_CHOICES
CATEGORY_MAP = {
    "GREETING": SignVideo.CATEGORY_GREETINGS,
    "SURVIVAL": SignVideo.CATEGORY_SURVIVAL,
    "NUMBER": SignVideo.CATEGORY_NUMBERS,
    "CALENDAR": SignVideo.CATEGORY_CALENDAR,
    "DAYS": SignVideo.CATEGORY_DAYS,
    "FAMILY": SignVideo.CATEGORY_FAMILY,
    "RELATIONSHIPS": SignVideo.CATEGORY_RELATIONSHIPS,
    "COLOR": SignVideo.CATEGORY_COLORS,
    "FOOD": SignVideo.CATEGORY_FOOD,
    "DRINK": SignVideo.CATEGORY_DRINK,
}


def slugify_key(label: str) -> str:
    key = label.strip().lower()
    key = re.sub(r"[^a-z0-9]+", "_", key)
    return f"fsl105_{key.strip('_')}"


def title_word(label: str) -> str:
    # "DON'T UNDERSTAND" -> "Don't Understand"; keep apostrophes.
    return " ".join(w.capitalize() for w in label.strip().split())


def transcode_to_mp4(src_bytes: bytes, ffmpeg_exe: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = Path(tmpdir) / "in.mov"
        dst_path = Path(tmpdir) / "out.mp4"
        src_path.write_bytes(src_bytes)

        cmd = [
            ffmpeg_exe, "-y", "-i", str(src_path),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "baseline",
            "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "128k",
            "-vf", "scale='min(720,iw)':-2",
            str(dst_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 or not dst_path.exists():
            raise RuntimeError(f"ffmpeg failed: {result.stderr[-2000:]}")
        return dst_path.read_bytes()


def main() -> None:
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    print(f"Using ffmpeg: {ffmpeg_exe}")

    labels = list(
        FSL105Clip.objects.values_list("label", "category").distinct().order_by("label")
    )
    print(f"Found {len(labels)} distinct FSL-105 labels")

    created = 0
    updated = 0
    failed = []

    for label, category in labels:
        clip = (
            FSL105Clip.objects.filter(label=label, split=FSL105Clip.SPLIT_TRAIN)
            .order_by("clip_id")
            .first()
        ) or FSL105Clip.objects.filter(label=label).order_by("clip_id").first()

        if not clip or not clip.video_data:
            print(f"  [skip] {label}: no clip/video_data found")
            failed.append(label)
            continue

        key = slugify_key(label)
        sv_category = CATEGORY_MAP.get(category, SignVideo.CATEGORY_PHRASES)
        word = title_word(label)

        try:
            mp4_bytes = transcode_to_mp4(bytes(clip.video_data), ffmpeg_exe)
        except Exception as exc:
            print(f"  [FAIL] {label} (clip {clip.clip_id}): {exc}")
            failed.append(label)
            continue

        sv, was_created = SignVideo.objects.get_or_create(
            key=key,
            defaults={
                "word": word,
                "category": sv_category,
                "is_published": True,
                "text_to_sign_only": False,
            },
        )
        sv.word = word
        sv.category = sv_category
        sv.is_published = True
        sv.text_to_sign_only = False
        sv.video.save(f"{key}.mp4", ContentFile(mp4_bytes), save=True)

        if was_created:
            created += 1
        else:
            updated += 1
        print(f"  [ok] {label} -> SignVideo(key={key}, category={sv_category}), {len(mp4_bytes)} bytes")

    print(
        f"\nDone. Created {created}, updated {updated}, failed {len(failed)}. "
        f"SignVideo rows now: {SignVideo.objects.count()}"
    )
    if failed:
        print("Failed labels:", failed)


if __name__ == "__main__":
    main()
