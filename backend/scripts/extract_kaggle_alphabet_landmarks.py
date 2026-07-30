"""Extract MediaPipe hand landmarks from the Kaggle FSL alphabet image dataset.

Source: https://www.kaggle.com/datasets/japorton/fsl-dataset
(11,700 images, 26 letter classes, ~450 images/letter, 300x300px)

Manually download and unzip the Kaggle dataset into
backend/datasets/raw/fsl_alphabet_kaggle/ before running this script. The
expected layout is one subfolder per letter, e.g.:
    backend/datasets/raw/fsl_alphabet_kaggle/A/*.jpg
    backend/datasets/raw/fsl_alphabet_kaggle/B/*.jpg
    ...
If the actual downloaded structure differs (e.g. a flat folder with
letter-prefixed filenames, or a nested extra directory level), adjust
_iter_labeled_images() below -- it's the only place that assumes folder
layout; everything after it (MediaPipe extraction, CSV writing) is
layout-agnostic.

Each image is run through MediaPipe Hands in static-image mode (these are
independent photos, not a video stream) to extract 21 landmarks. Images
where no hand is detected are skipped and counted for QA.

Output matches the same CSV schema backend/scripts/train_fingerspelling_model.py
already reads from backend/datasets/fingerspelling/*.csv, so no changes are
needed there.

Usage (run under backend/.venv-training, NOT the main backend/.venv --
see backend/requirements-training.txt):
    python scripts/extract_kaggle_alphabet_landmarks.py [path/to/fsl_alphabet_kaggle]
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path
from typing import Iterator, Tuple

import cv2
import mediapipe as mp
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_DIR = BACKEND_DIR / "datasets" / "raw" / "fsl_alphabet_kaggle"
OUTPUT_CSV_PATH = BACKEND_DIR / "datasets" / "fingerspelling" / "kaggle_extracted.csv"
CLASS_LABELS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


def _iter_labeled_images(root: Path) -> Iterator[Tuple[str, Path]]:
    """Yields (letter_label, image_path) pairs.

    Finds every subfolder anywhere under `root` whose name is exactly one
    A-Z letter (case-insensitive) and yields its images directly (not
    recursing further, so a per-letter folder containing its own nested
    junk doesn't matter) -- this handles both a flat root/A/1.jpg layout and
    a wrapped layout like root/Collated/A/1.jpg without hardcoding the
    wrapper folder name. Skips images that are exact duplicates of an
    already-seen image (by original stem, ignoring Roboflow-style
    "_jpg.rf.<hash>" augmentation suffixes) is NOT done here -- every image
    file found is used, since augmented crops are still valid training
    signal for a landmark-based (not pixel-based) classifier.
    """
    letter_dirs: dict[str, list[Path]] = {}
    for subdir in root.rglob("*"):
        if not subdir.is_dir():
            continue
        label = subdir.name.strip().upper()
        if label in CLASS_LABELS:
            letter_dirs.setdefault(label, []).append(subdir)

    if not letter_dirs:
        return

    for label in sorted(letter_dirs):
        for subdir in letter_dirs[label]:
            for image_path in sorted(subdir.iterdir()):
                if image_path.is_file() and image_path.suffix.lower() in IMAGE_EXTENSIONS:
                    yield label, image_path


def main() -> None:
    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT_DIR
    if not input_dir.exists() or not any(input_dir.iterdir()):
        print(f"No data found at {input_dir}.")
        print(
            "Download https://www.kaggle.com/datasets/japorton/fsl-dataset manually, "
            f"unzip it, and place the per-letter subfolders under {input_dir}/"
        )
        return

    mp_hands = mp.solutions.hands
    rows_written = 0
    skipped_no_hand = 0
    counts: Counter = Counter()

    OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with mp_hands.Hands(static_image_mode=True, max_num_hands=1, min_detection_confidence=0.5) as hands, \
            OUTPUT_CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        header = ["label", "handedness"] + [f"{axis}{i}" for i in range(21) for axis in ("x", "y", "z")]
        writer.writerow(header)

        for label, image_path in _iter_labeled_images(input_dir):
            image_bgr = cv2.imread(str(image_path))
            if image_bgr is None:
                skipped_no_hand += 1
                continue

            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            results = hands.process(image_rgb)

            if not results.multi_hand_landmarks:
                skipped_no_hand += 1
                continue

            landmarks = results.multi_hand_landmarks[0].landmark
            handedness = "Right"
            if results.multi_handedness:
                handedness = results.multi_handedness[0].classification[0].label

            flat = np.asarray([[lm.x, lm.y, lm.z] for lm in landmarks], dtype=np.float64).reshape(-1)
            writer.writerow([label, handedness] + [f"{v:.8f}" for v in flat])
            rows_written += 1
            counts[label] += 1

    print(f"Wrote {rows_written} rows to {OUTPUT_CSV_PATH}")
    print(f"Skipped {skipped_no_hand} images with no detected hand.")
    print("\nPer-letter counts:")
    for label in sorted(counts):
        print(f"  {label}: {counts[label]}")
    missing = sorted(CLASS_LABELS - set(counts))
    if missing:
        print(f"\nNo real data extracted for: {', '.join(missing)}.")
    print(
        "\nNext: run backend/scripts/train_fingerspelling_model.py "
        "(under the main backend/.venv, not .venv-training) to retrain including this data."
    )


if __name__ == "__main__":
    main()
