"""Extract two-hand MediaPipe landmark sequences from the FSL-105 video dataset.

Source: Mendeley Data, "FSL105: The Video Filipino Sign Language Sign
Database of Introductory 105 FSL Signs" (Tupal & Cabatuan), CC BY 4.0.
https://data.mendeley.com/datasets/48y2y99mb9/2
2,130 four-second clips, 105 FSL words/phrases, with train.csv/test.csv/labels.csv.

Manually download and unzip the dataset into
backend/datasets/raw/fsl_105_mendeley/ before running this script. Expected
layout (adjust _iter_clips() below if the actual download differs):
    backend/datasets/raw/fsl_105_mendeley/train.csv
    backend/datasets/raw/fsl_105_mendeley/test.csv
    backend/datasets/raw/fsl_105_mendeley/labels.csv
    backend/datasets/raw/fsl_105_mendeley/videos/<clip files referenced by the CSVs>

Each video clip is run through MediaPipe Hands in video mode (2 hands, with
tracking continuity across frames) at a fixed subsample rate matching
collect-phrases.html's ~80ms recording cadence, so training-time and
inference-time temporal resolution stay comparable.

Output: two JSONL files matching the schema collect-phrases.html now exports
(see word_sequence_svc.py / train_word_model.py):
    {"label": "HELLO", "frames": [{"left": [[x,y,z]]*21|null, "right": [...]|null}, ...], "duration_ms": ...}
written as fsl105_extracted_train.jsonl / fsl105_extracted_test.jsonl,
respecting FSL-105's own train/test split (not a random re-split) so
held-out evaluation doesn't leak the same signer across train and test.

Usage (run under backend/.venv-training, NOT the main backend/.venv --
see backend/requirements-training.txt):
    python scripts/extract_fsl105_landmarks.py [path/to/fsl_105_mendeley]
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Dict, Iterator, List, Optional

import cv2
import mediapipe as mp

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_DIR = BACKEND_DIR / "datasets" / "raw" / "fsl_105_mendeley"
OUTPUT_DIR = BACKEND_DIR / "datasets" / "phrases"
SAMPLE_INTERVAL_MS = 80  # matches collect-phrases.html's SAMPLE_INTERVAL_MS
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}


def _find_split_csv(input_dir: Path, name: str) -> Optional[Path]:
    matches = list(input_dir.rglob(name))
    return matches[0] if matches else None


def _find_video_file(input_dir: Path, vid_path_hint: str, csv_path: Path) -> Optional[Path]:
    """Resolves a vid_path value from train.csv/test.csv (e.g. "clips\\17\\6.MOV",
    Windows-backslash-separated) to an actual file on disk.

    IMPORTANT: this must match on the FULL relative path (parent folder +
    filename), never on filename alone. FSL-105's clips are numbered per-word
    folder (clips/<word_id>/<attempt>.MOV), so many different words share the
    same attempt-number filename (e.g. both clips/17/6.MOV and clips/74/6.MOV
    exist) -- a filename-only search would silently return the wrong clip for
    a different word, corrupting every label.
    """
    normalized = vid_path_hint.replace("\\", "/")
    relative_parts = Path(normalized).parts  # e.g. ("clips", "17", "6.MOV")

    # The clips/ folder is a sibling of the CSV, but possibly nested one level
    # deeper (e.g. inside "FSL-105 A dataset for recognizing ...MOV").
    # Resolve from the CSV's own directory, which is the actual dataset root.
    dataset_root = csv_path.parent
    direct = dataset_root / normalized
    if direct.exists():
        return direct
    direct_ci = dataset_root / normalized.lower()
    if direct_ci.exists():
        return direct_ci

    if len(relative_parts) >= 2:
        word_folder, filename = relative_parts[-2], relative_parts[-1]
        stem = Path(filename).stem
        for ext in VIDEO_EXTENSIONS:
            candidates = list(dataset_root.rglob(f"{word_folder}/{stem}{ext}"))
            candidates += list(dataset_root.rglob(f"{word_folder}/{stem}{ext.upper()}"))
            if candidates:
                return candidates[0]

    return None


def _iter_clips(input_dir: Path, split_csv_name: str) -> Iterator[tuple[str, Path]]:
    """Yields (label, video_path) pairs for one split (train.csv or test.csv).

    FSL-105's train.csv/test.csv columns are: vid_path,id_label,label,category
    (vid_path e.g. "clips\\17\\6.MOV", label e.g. "HOW ARE YOU").
    """
    csv_path = _find_split_csv(input_dir, split_csv_name)
    if csv_path is None:
        print(f"Could not find {split_csv_name} anywhere under {input_dir}.")
        return

    with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = [f.strip().lower() for f in (reader.fieldnames or [])]
        file_col = next((f for f in reader.fieldnames or [] if f.strip().lower() in {"vid_path", "filename", "file", "video", "clip"}), None)
        label_col = next((f for f in reader.fieldnames or [] if f.strip().lower() in {"label", "gloss", "sign", "class"}), None)

        if not file_col or not label_col:
            print(
                f"Could not identify filename/label columns in {csv_path} "
                f"(found columns: {fieldnames}). Update _iter_clips() with the actual column names."
            )
            return

        for row in reader:
            vid_path_hint = str(row[file_col]).strip()
            label = str(row[label_col]).strip().upper()
            if not vid_path_hint or not label:
                continue
            video_path = _find_video_file(input_dir, vid_path_hint, csv_path)
            if video_path is None:
                continue
            yield label, video_path


def _extract_sequence(video_path: Path, mp_hands) -> Optional[List[Dict[str, Optional[list]]]]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_stride = max(1, round(fps * (SAMPLE_INTERVAL_MS / 1000.0)))

    frames: List[Dict[str, Optional[list]]] = []
    frame_idx = 0
    # A fresh Hands() per clip: in video/tracking mode (static_image_mode=False)
    # MediaPipe carries an internal ROI from the previous processed frame to
    # speed up re-detection. Reusing one Hands() instance across unrelated
    # clips leaks that ROI from the end of one video into the start of the
    # next, causing spurious all-null sequences even when hands are clearly
    # visible. Each clip gets its own tracking state instead.
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


def _process_split(input_dir: Path, split_csv_name: str, output_path: Path) -> None:
    mp_hands = mp.solutions.hands
    written = 0
    skipped_no_hand = 0
    skipped_unreadable = 0

    with output_path.open("w", encoding="utf-8") as out_handle:
        for i, (label, video_path) in enumerate(_iter_clips(input_dir, split_csv_name)):
            frames = _extract_sequence(video_path, mp_hands)
            if frames is None:
                skipped_unreadable += 1
                continue
            if not any(f["left"] is not None or f["right"] is not None for f in frames):
                skipped_no_hand += 1
                continue

            record = {"label": label, "frames": frames, "duration_ms": len(frames) * SAMPLE_INTERVAL_MS}
            out_handle.write(json.dumps(record) + "\n")
            out_handle.flush()
            written += 1

            if (i + 1) % 100 == 0:
                print(f"  ...{split_csv_name}: processed {i + 1} clips ({written} written, "
                      f"{skipped_no_hand} no-hand, {skipped_unreadable} unreadable so far)", flush=True)

    print(f"{split_csv_name}: wrote {written} sequences to {output_path} "
          f"(skipped {skipped_unreadable} unreadable, {skipped_no_hand} with no hand detected in any frame).")


def main() -> None:
    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT_DIR
    if not input_dir.exists() or not any(input_dir.iterdir()):
        print(f"No data found at {input_dir}.")
        print(
            "Download the FSL-105 dataset manually from "
            "https://data.mendeley.com/datasets/48y2y99mb9/2 (CC BY 4.0), unzip it, "
            f"and place its contents (train.csv/test.csv/labels.csv + video files) under {input_dir}/"
        )
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _process_split(input_dir, "train.csv", OUTPUT_DIR / "fsl105_extracted_train.jsonl")
    _process_split(input_dir, "test.csv", OUTPUT_DIR / "fsl105_extracted_test.jsonl")

    print(
        "\nNext: run backend/scripts/train_word_model.py "
        "(under the main backend/.venv, not .venv-training) to train on this data. "
        "It reads every *.jsonl under backend/datasets/phrases/, so both split files will be combined "
        "unless you evaluate them separately for a rigorous held-out check (see the project plan's verification section)."
    )


if __name__ == "__main__":
    main()
