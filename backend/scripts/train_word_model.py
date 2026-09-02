"""Train the word/phrase sequence classifier from real recorded gesture data.

Reads every *.jsonl under backend/datasets/phrases/ (exported by
collect-phrases.html), where each line is a JSON object:
    {"label": "HELLO", "frames": [{"left": [[x,y,z]*21]|null, "right": [...]|null}, ...], "duration_ms": 2500}

Turns each sequence into the fixed-length feature vector used by
signtext.word_sequence_svc, trains a StandardScaler+SVC classifier, and
saves it to the exact MODEL_PATH the runtime module already expects.

There is no synthetic filler here (unlike the fingerspelling trainer):
a word gesture can't be reasonably hand-guessed, so only phrases with real
recorded sequences will ever be recognized by the deployed model.

Usage (from the backend/ directory, with the virtualenv active):
    python scripts/train_word_model.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from signtext.word_sequence_svc import MODEL_PATH, extract_sequence_features  # noqa: E402

DATASET_DIR = BACKEND_DIR / "datasets" / "phrases"
MANIFEST_PATH = MODEL_PATH.parent / "word_sequence_svc.meta.json"
MIN_SAMPLES_PER_PHRASE_FOR_EVAL = 2


def _mirror_frames(frames: list[dict]) -> list[dict]:
    """Flips a frame sequence left<->right (x -> 1-x on each landmark).

    FSL-105's clips were filmed of a signer facing the camera third-person,
    while the deployed app runs a selfie-view webcam feed straight through
    MediaPipe -- so which physical hand MediaPipe calls "Left" vs "Right"
    for the same real-world gesture depends on camera/device conventions
    that vary per setup. A model trained only on the dataset's own
    handedness convention collapses to ~13% accuracy (vs 99%) the moment a
    live user's feed happens to report the opposite handedness for a given
    hand -- see the investigation that added this function. Mirroring every
    training sequence (flipping x and swapping the left/right slots) and
    training on both orientations makes the model handedness-invariant
    instead of trying to guess/normalize orientation at inference time.
    """
    mirrored = []
    for frame in frames:
        left = frame.get("left")
        right = frame.get("right")
        new_left = [[1.0 - pt[0], pt[1], pt[2]] for pt in right] if right is not None else None
        new_right = [[1.0 - pt[0], pt[1], pt[2]] for pt in left] if left is not None else None
        mirrored.append({"left": new_left, "right": new_right})
    return mirrored


def load_sequences() -> tuple[np.ndarray, np.ndarray, Counter, np.ndarray]:
    jsonl_files = sorted(DATASET_DIR.glob("*.jsonl"))
    features: list[np.ndarray] = []
    labels: list[str] = []
    groups: list[int] = []
    skipped = 0

    for jsonl_path in jsonl_files:
        with jsonl_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    skipped += 1
                    continue

                label = str(record.get("label", "")).strip().upper()
                frames = record.get("frames")
                if not label or not isinstance(frames, list):
                    skipped += 1
                    continue

                feature_vector = extract_sequence_features(frames)
                if feature_vector is None:
                    skipped += 1
                    continue

                clip_group = len(features)  # groups a clip with its mirror below
                features.append(feature_vector.reshape(-1))
                labels.append(label)
                groups.append(clip_group)

                mirrored_vector = extract_sequence_features(_mirror_frames(frames))
                if mirrored_vector is not None:
                    features.append(mirrored_vector.reshape(-1))
                    labels.append(label)
                    groups.append(clip_group)

    if skipped:
        print(f"Skipped {skipped} malformed/too-short sequences across {len(jsonl_files)} file(s).")

    if not features:
        return np.zeros((0, 0)), np.asarray([]), Counter(), np.asarray([])

    return np.vstack(features), np.asarray(labels), Counter(labels), np.asarray(groups)


def evaluate(x: np.ndarray, y: np.ndarray, counts: Counter, groups: np.ndarray) -> float | None:
    usable_labels = {label for label, count in counts.items() if count >= MIN_SAMPLES_PER_PHRASE_FOR_EVAL}
    if len(usable_labels) < 2:
        print("Not enough phrases with >=2 samples yet for a held-out accuracy check.")
        return None

    mask = np.asarray([label in usable_labels for label in y])
    x_eval, y_eval, groups_eval = x[mask], y[mask], groups[mask]

    # Split by clip group (not by row) so a clip and its mirrored twin always
    # land on the same side -- otherwise the split leaks a near-duplicate of
    # every test row into training and the held-out score is inflated.
    unique_groups = np.unique(groups_eval)
    group_labels = np.asarray([y_eval[groups_eval == g][0] for g in unique_groups])
    train_groups, test_groups = train_test_split(
        unique_groups, test_size=0.25, stratify=group_labels, random_state=42
    )
    train_mask = np.isin(groups_eval, train_groups)
    test_mask = np.isin(groups_eval, test_groups)
    x_train, x_test = x_eval[train_mask], x_eval[test_mask]
    y_train, y_test = y_eval[train_mask], y_eval[test_mask]

    model = make_pipeline(StandardScaler(), SVC(kernel="rbf", C=5.0, gamma="scale", probability=True))
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    accuracy = float(accuracy_score(y_test, predictions))

    print(f"\nHeld-out accuracy on real recorded phrases: {accuracy * 100:.1f}% ({len(y_test)} test rows)")
    print(classification_report(y_test, predictions, zero_division=0))
    return accuracy


def main() -> None:
    x, y, counts, groups = load_sequences()

    print(f"Loaded {len(y)} sequences (original + mirrored) covering {len(counts)} phrase(s).")
    for label, count in sorted(counts.items()):
        print(f"  {label}: {count} sequences")

    if len(y) == 0:
        print(
            f"\nNo JSONL files found in {DATASET_DIR}. "
            "Record data with collect-phrases.html, export a .jsonl into that folder, and re-run this script."
        )
        return

    if len(counts) < 2:
        print(
            "\nNeed at least 2 distinct phrases with recorded data to train a classifier. "
            "Record at least one more phrase and re-run."
        )
        return

    held_out_accuracy = evaluate(x, y, counts, groups)

    print(f"\nTraining deployed model on all {len(y)} recorded sequences...")
    final_model = make_pipeline(StandardScaler(), SVC(kernel="rbf", C=5.0, gamma="scale", probability=True))
    final_model.fit(x, y)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, MODEL_PATH)

    manifest = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "total_sequences": int(len(y)),
        "phrases": {label: int(count) for label, count in counts.items()},
        "held_out_accuracy": held_out_accuracy,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\nSaved model to {MODEL_PATH}")
    print(f"Saved training manifest to {MANIFEST_PATH}")
    print(f"\nOnly these {len(counts)} phrase(s) will be recognized by the local model: {', '.join(sorted(counts))}")
    print("Restart the Django server so it picks up the newly trained model.")


if __name__ == "__main__":
    main()
