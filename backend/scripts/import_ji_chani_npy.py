"""Import the pre-extracted FSL alphabet landmark dataset from ji-chani/MediaPipe-FSL-Alphabet.

Source: https://github.com/ji-chani/MediaPipe-FSL-Alphabet
(FSL_img_dataset_MediaPipe_24classes.npy, CC-equivalent open GitHub repo,
2,130+ real FSL fingerspelling photos run through MediaPipe by the repo's
authors, one row per hand-landmark set).

The .npy stores a pickled dict: {"data": [...], "target": [...], "path": [...]}
- data[i] is either a 63-dim float array (21 landmarks x [x,y,z], flattened)
  or None when MediaPipe found no hand in that source image.
- target[i] is a single uppercase letter (24 classes -- excludes J and Z,
  which require motion and can't be captured by a static photo).

This script converts the valid (non-None) rows into the same CSV schema
backend/scripts/train_fingerspelling_model.py already reads from
backend/datasets/fingerspelling/*.csv (label, handedness, x0,y0,z0, ..., x20,y20,z20),
so the existing trainer picks these up with zero changes.

Usage (run under backend/.venv-training, NOT the main backend/.venv --
see backend/requirements-training.txt):
    python scripts/import_ji_chani_npy.py [path/to/FSL_img_dataset_MediaPipe_24classes.npy]

If no path is given, defaults to backend/datasets/raw/FSL_img_dataset_MediaPipe_24classes.npy.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_NPY_PATH = BACKEND_DIR / "datasets" / "raw" / "FSL_img_dataset_MediaPipe_24classes.npy"
OUTPUT_CSV_PATH = BACKEND_DIR / "datasets" / "fingerspelling" / "ji_chani_24classes.csv"
LANDMARK_COUNT = 21
COORDS_PER_LANDMARK = 3


def main() -> None:
    npy_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_NPY_PATH
    if not npy_path.exists():
        print(f"Dataset not found at {npy_path}.")
        print(
            "Download it first, e.g.:\n"
            "  curl -L -o "
            f'"{DEFAULT_NPY_PATH}" '
            "https://raw.githubusercontent.com/ji-chani/MediaPipe-FSL-Alphabet/main/FSL_img_dataset_MediaPipe_24classes.npy"
        )
        return

    raw = np.load(npy_path, allow_pickle=True)
    dataset = raw.item()
    data = dataset["data"]
    targets = dataset["target"]

    rows_written = 0
    skipped_none = 0
    skipped_bad_shape = 0
    counts: Counter = Counter()

    OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        header = ["label", "handedness"] + [
            f"{axis}{i}" for i in range(LANDMARK_COUNT) for axis in ("x", "y", "z")
        ]
        writer.writerow(header)

        for sample, label in zip(data, targets):
            if sample is None:
                skipped_none += 1
                continue

            arr = np.asarray(sample, dtype=np.float64)
            if arr.shape != (LANDMARK_COUNT * COORDS_PER_LANDMARK,):
                skipped_bad_shape += 1
                continue

            label = str(label).strip().upper()
            # Dataset doesn't record handedness; the runtime feature extractor
            # already treats handedness as cosmetic (side-agnostic geometry),
            # so "Right" is a safe, harmless default for every row.
            writer.writerow([label, "Right"] + [f"{v:.8f}" for v in arr])
            rows_written += 1
            counts[label] += 1

    print(f"Wrote {rows_written} rows to {OUTPUT_CSV_PATH}")
    print(f"Skipped {skipped_none} rows with no detected hand (None), {skipped_bad_shape} with unexpected shape.")
    print("\nPer-letter counts:")
    for label in sorted(counts):
        print(f"  {label}: {counts[label]}")
    missing = sorted(set("ABCDEFGHIJKLMNOPQRSTUVWXYZ") - set(counts))
    if missing:
        print(f"\nNo real data for: {', '.join(missing)} (this dataset excludes J/Z; synthetic fill will cover them).")
    print(
        f"\nNext: run backend/scripts/train_fingerspelling_model.py "
        "(under the main backend/.venv, not .venv-training) to retrain on this real data."
    )


if __name__ == "__main__":
    main()
