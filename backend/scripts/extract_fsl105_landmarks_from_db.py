"""Extract two-hand MediaPipe landmark sequences from the FSL105Clip DB table.

Supersedes extract_fsl105_landmarks.py's file-based input: the FSL-105
dataset's 2,130 video clips are no longer read from disk -- they were
imported into the database itself (backend/scripts/import_fsl105.py),
stored as raw bytes in FSL105Clip.video_data (Postgres BYTEA). This script
reads those bytes straight from the DB, decodes each clip in-memory via a
temp file (OpenCV's VideoCapture needs a real file path/handle, not a byte
buffer), and runs it through MediaPipe Hands exactly like the file-based
version did.

Output: same JSONL schema collect-phrases.html exports and
train_word_model.py already reads (unchanged output paths, so this is a
drop-in swap of the input source, not a new training step):
    backend/datasets/phrases/fsl105_extracted_train.jsonl
    backend/datasets/phrases/fsl105_extracted_test.jsonl

Usage (run under backend/.venv-training, NOT the main backend/.venv --
see backend/requirements-training.txt):
    python scripts/extract_fsl105_landmarks_from_db.py

To pull from a different database than the one in backend/.env (e.g. the
Render production Postgres instead of local), set these env vars first:
    USE_POSTGRES=True
    POSTGRES_DB=...
    POSTGRES_USER=...
    POSTGRES_PASSWORD=...
    POSTGRES_HOST=...
    POSTGRES_PORT=...
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import mediapipe as mp

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kumpas_api.settings")
import django  # noqa: E402

django.setup()

from signtext.models import FSL105Clip  # noqa: E402

OUTPUT_DIR = BACKEND_DIR / "datasets" / "phrases"
SAMPLE_INTERVAL_MS = 80  # matches collect-phrases.html's SAMPLE_INTERVAL_MS


def _extract_sequence(video_bytes: bytes, suffix: str, mp_hands) -> Optional[List[Dict[str, Optional[list]]]]:
    # cv2.VideoCapture needs a real file path -- write the DB blob to a temp
    # file for the duration of this one clip, then discard it.
    with tempfile.NamedTemporaryFile(suffix=suffix or ".mov", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    try:
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            return None

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_stride = max(1, round(fps * (SAMPLE_INTERVAL_MS / 1000.0)))

        frames: List[Dict[str, Optional[list]]] = []
        frame_idx = 0
        # A fresh Hands() per clip: in video/tracking mode MediaPipe carries
        # an internal ROI from the previous processed frame, which would
        # otherwise leak tracking state from one clip into the next.
        with mp_hands.Hands(static_image_mode=False, max_num_hands=2, min_detection_confidence=0.5, min_tracking_confidence=0.5) as hands:
            while True:
                ok, frame_bgr = cap.read()
                if not ok:
                    break
                if frame_idx % frame_stride == 0:
                    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                    results = hands.process(frame_rgb)

                    left = None
                    right = None
                    if results.multi_hand_landmarks and results.multi_handedness:
                        for handedness_info, hand_landmarks in zip(results.multi_handedness, results.multi_hand_landmarks):
                            label = handedness_info.classification[0].label
                            coords = [[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark]
                            if label == "Left":
                                left = coords
                            elif label == "Right":
                                right = coords

                    frames.append({"left": left, "right": right})
                frame_idx += 1

        cap.release()
        return frames if len(frames) >= 4 else None
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _process_split(split_name: str, output_path: Path, mp_hands) -> None:
    written = 0
    skipped_no_hand = 0
    skipped_unreadable = 0
    skipped_empty = 0

    queryset = FSL105Clip.objects.filter(split=split_name).order_by("clip_id")
    total = queryset.count()

    with output_path.open("w", encoding="utf-8") as out_handle:
        for i, clip in enumerate(queryset.iterator()):
            if not clip.video_data:
                skipped_empty += 1
                continue

            suffix = Path(clip.video_filename or "").suffix or ".mov"
            frames = _extract_sequence(bytes(clip.video_data), suffix, mp_hands)
            if frames is None:
                skipped_unreadable += 1
                continue
            if not any(f["left"] is not None or f["right"] is not None for f in frames):
                skipped_no_hand += 1
                continue

            record = {"label": clip.label, "frames": frames, "duration_ms": len(frames) * SAMPLE_INTERVAL_MS}
            out_handle.write(json.dumps(record) + "\n")
            out_handle.flush()
            written += 1

            if (i + 1) % 100 == 0:
                print(
                    f"  ...{split_name}: processed {i + 1}/{total} clips ({written} written, "
                    f"{skipped_no_hand} no-hand, {skipped_unreadable} unreadable so far)",
                    flush=True,
                )

    print(
        f"{split_name}: wrote {written} sequences to {output_path} "
        f"(skipped {skipped_unreadable} unreadable, {skipped_no_hand} with no hand detected, "
        f"{skipped_empty} with empty video_data)."
    )


def main() -> None:
    total_clips = FSL105Clip.objects.count()
    if total_clips == 0:
        print(
            "No FSL105Clip rows found in the database. "
            "Run backend/scripts/import_fsl105.py first to load the dataset."
        )
        return

    print(f"Found {total_clips} FSL105Clip rows in the database.")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    mp_hands = mp.solutions.hands
    _process_split("train", OUTPUT_DIR / "fsl105_extracted_train.jsonl", mp_hands)
    _process_split("test", OUTPUT_DIR / "fsl105_extracted_test.jsonl", mp_hands)

    print(
        "\nNext: run backend/scripts/train_word_model.py "
        "(under the main backend/.venv, not .venv-training) to train on this data."
    )


if __name__ == "__main__":
    main()
