"""Import the FSL-105 dataset (Mendeley 48y2y99mb9) into the FSL105Clip table.

Source: https://data.mendeley.com/datasets/48y2y99mb9/2
105 Filipino Sign Language classes, 2,130 four-second video clips, split
80/20 into train.csv / test.csv.

Mendeley blocks scripted downloads behind a Cloudflare challenge, so this
dataset must be downloaded by hand:
  1. Open https://data.mendeley.com/datasets/48y2y99mb9/2 in a browser and
     use "Download all".
  2. Extract the outer zip, then extract the clips.zip inside it too, into
     backend/datasets/fsl105/ so you end up with:
       backend/datasets/fsl105/train.csv
       backend/datasets/fsl105/test.csv
       backend/datasets/fsl105/labels.csv
       backend/datasets/fsl105/clips/<id_label>/<n>.MOV

train.csv / test.csv columns: vid_path, id_label, label, category
  e.g. "clips\\17\\6.MOV", 17, "CORRECT", "SURVIVAL"

Then run, from the backend/ directory with the main venv active:
    python scripts/import_fsl105.py [path/to/backend/datasets/fsl105]

For every row in train.csv/test.csv this copies the referenced video file
into Django media storage (fsl105_clips/YYYY/MM/DD/...) via FSL105Clip.video
and creates/updates one FSL105Clip row. clip_id is assigned as
"<id_label>_<clip number>" (e.g. "17_6") derived from vid_path, which is
stable across re-runs, so running this script again is idempotent.
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
from pathlib import PureWindowsPath

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kumpas_api.settings")
import django  # noqa: E402

django.setup()

from django.core.files import File  # noqa: E402
from signtext.models import FSL105Clip  # noqa: E402

DEFAULT_DATASET_DIR = BACKEND_DIR / "datasets" / "fsl105"


def _clip_id_from_vid_path(vid_path: str) -> int:
    """"clips\\17\\6.MOV" -> label 17, clip 6 -> numeric id 17006 (label*1000 + clip).

    Clip numbers within a label top out well under 1000 (~20 per label), so
    this stays collision-free while keeping clip_id a plain integer to match
    FSL105Clip.clip_id's PositiveIntegerField.
    """
    parts = PureWindowsPath(vid_path).parts
    label_id = int(parts[-2])
    clip_num = int(PureWindowsPath(parts[-1]).stem)
    return label_id * 1000 + clip_num


def _import_split(dataset_dir: Path, split_name: str, csv_name: str) -> tuple[int, int, int]:
    csv_path = dataset_dir / csv_name
    if not csv_path.exists():
        print(f"Skipping {split_name}: {csv_path} not found.")
        return (0, 0, 0)

    created = 0
    updated = 0
    skipped = 0

    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            vid_path = row["vid_path"].strip()
            word = row["label"].strip()
            category = row["category"].strip()
            clip_id = _clip_id_from_vid_path(vid_path)

            video_path = (dataset_dir / PureWindowsPath(vid_path).as_posix()).resolve()
            if not video_path.exists():
                print(f"  [{split_name}] clip {clip_id} ({word}): video not found at {video_path}, skipping.")
                skipped += 1
                continue

            obj, was_created = FSL105Clip.objects.get_or_create(
                clip_id=clip_id,
                defaults={
                    "label": word,
                    "category": category,
                    "split": split_name,
                    "source_path": vid_path,
                },
            )
            if not obj.video:
                with video_path.open("rb") as fh:
                    obj.video.save(f"{clip_id}_{video_path.name}", File(fh), save=False)
            obj.label = word
            obj.category = category
            obj.split = split_name
            obj.source_path = vid_path
            obj.save()

            if was_created:
                created += 1
            else:
                updated += 1

    return (created, updated, skipped)


def main() -> None:
    dataset_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_DATASET_DIR
    if not dataset_dir.exists():
        print(f"Dataset folder not found: {dataset_dir}")
        print("Download and extract the FSL-105 dataset first -- see the module docstring for instructions.")
        return

    print(f"Reading dataset from {dataset_dir}")

    total_created = total_updated = total_skipped = 0
    for split_name, csv_name in (("train", "train.csv"), ("test", "test.csv")):
        created, updated, skipped = _import_split(dataset_dir, split_name, csv_name)
        print(f"{split_name}: created {created}, updated {updated}, skipped {skipped}")
        total_created += created
        total_updated += updated
        total_skipped += skipped

    print(
        f"\nDone. Total created {total_created}, updated {total_updated}, "
        f"skipped {total_skipped}. FSL105Clip rows now: {FSL105Clip.objects.count()}"
    )


if __name__ == "__main__":
    main()
