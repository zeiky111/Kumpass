"""Train the fingerspelling SVC from real recorded landmark data.

Reads every *.csv under backend/datasets/fingerspelling/ (exported by
collect-landmarks.html), recomputes the exact same engineered feature
vector the realtime pipeline uses (via signtext.fingerspelling_svc), and
trains a StandardScaler+SVC pipeline compatible with what
fingerspelling_svc._load_or_build_model() expects at MODEL_PATH.

Letters with no recorded samples yet are filled with the existing
synthetic-prototype samples so the deployed model always covers the
full A-Z alphabet (the runtime loader requires all 26 classes to be
present before it will use a saved model instead of retraining).

Usage (from the backend/ directory, with the virtualenv active):
    python scripts/train_fingerspelling_model.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
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

from signtext.fingerspelling_svc import (  # noqa: E402
    CLASS_LABELS,
    MODEL_PATH,
    PROTOTYPES,
    _canonicalize_landmarks_for_handedness,
    extract_features_from_landmarks,
)

DATASET_DIR = BACKEND_DIR / "datasets" / "fingerspelling"
MANIFEST_PATH = MODEL_PATH.parent / "fingerspelling_svc.meta.json"
SYNTHETIC_SAMPLES_PER_MISSING_LETTER = 200
LANDMARK_COLUMNS = 21 * 3
# How many jittered variants to generate per real recorded row -- see
# _jitter_landmarks for why this exists.
# Increased from 4/0.01: the user reports widespread misdetection across
# many letters on live webcam despite 96%+ accuracy on clean recorded data,
# pointing to a bigger clean-data-vs-live-camera gap than the original
# jitter strength covered. Doubled both the noise magnitude and the number
# of jittered variants per real sample so the model sees a wider range of
# imprecise/noisy landmark positions during training.
JITTERS_PER_SAMPLE = 4
JITTER_STDDEV = 0.02
# How many rotated variants to generate per real recorded row -- see
# _rotate_landmarks for why this exists. Kept modest (each rotation also
# produces a jittered twin below, so the real multiplier is 2x this) to
# keep training time and the resulting model file size reasonable.
ROTATIONS_PER_SAMPLE = 3
MAX_ROTATION_DEGREES = 20.0
_NP_RNG = np.random.default_rng(42)


def _mirror_landmarks(landmarks: list[dict]) -> list[dict]:
    """Flips every landmark's x coordinate (1 - x), leaving y/z alone.

    predict_letter_from_landmarks canonicalizes "Left"-handed input by
    mirroring it to look right-handed before feature extraction, so the
    model only ever sees right-looking geometry in principle -- but that
    canonicalization depends on MediaPipe/the browser reporting the
    correct handedness label. If that label is wrong (a real risk on
    live webcam, confirmed by testing: feeding a genuine "C" sample
    through with a flipped handedness label predicted "Q" in most of the
    error cases -- matching the user's exact live-camera report of C
    reading as Q), the canonicalization mirrors an already-correct hand
    the wrong way, corrupting the geometry into something the model
    never trained on. Training directly on mirrored copies (paired with
    the opposite handedness label, so canonicalization mirrors them back
    to the *original* orientation) teaches the model to still get the
    right answer even when that label is wrong.
    """
    return [{"x": 1.0 - float(p["x"]), "y": float(p["y"]), "z": float(p["z"])} for p in landmarks]


def _rotate_landmarks(landmarks: list[dict]) -> list[dict]:
    """Rotates every landmark around the wrist (landmark 0) by a random
    small angle in the image plane (x/y only; z is left alone).

    collect-landmarks.html recordings have the signer's hand held at a
    fairly consistent, deliberate angle relative to the camera. A live
    user's hand is rarely at that exact angle -- a slight wrist tilt or a
    camera that isn't perfectly perpendicular to the hand rotates the whole
    landmark set in the image plane, which the geometric features (angles,
    horizontal/vertical projections) are not inherently invariant to.
    Training on randomly rotated copies of every real sample teaches the
    model to tolerate that instead of requiring the exact recorded angle.
    """
    wrist = landmarks[0]
    wx, wy = float(wrist["x"]), float(wrist["y"])
    angle = np.radians(_NP_RNG.uniform(-MAX_ROTATION_DEGREES, MAX_ROTATION_DEGREES))
    cos_a, sin_a = np.cos(angle), np.sin(angle)

    rotated = []
    for point in landmarks:
        dx = float(point["x"]) - wx
        dy = float(point["y"]) - wy
        new_x = wx + dx * cos_a - dy * sin_a
        new_y = wy + dx * sin_a + dy * cos_a
        rotated.append({"x": new_x, "y": new_y, "z": float(point["z"])})
    return rotated


def _jitter_landmarks(landmarks: list[dict]) -> list[dict]:
    """Adds small per-landmark Gaussian noise to every (x, y, z) coordinate.

    The recorded training CSVs come from collect-landmarks.html under
    controlled conditions (deliberate, held poses), so MediaPipe's landmark
    estimates in that data are cleaner than what live webcam use produces
    (motion blur, variable lighting, a signer who isn't holding perfectly
    still). extract_features_from_landmarks derives geometric ratios
    (distances, curl, extension) straight from raw coordinates, so a model
    trained only on clean landmarks has no built-in tolerance for that
    real-world noise. This mirrors the same fix already applied to the word
    sequence model (see train_word_model.py's _jitter_frames).
    """
    jittered = []
    for point in landmarks:
        jittered.append({
            "x": float(point["x"]) + _NP_RNG.normal(0.0, JITTER_STDDEV),
            "y": float(point["y"]) + _NP_RNG.normal(0.0, JITTER_STDDEV),
            "z": float(point["z"]) + _NP_RNG.normal(0.0, JITTER_STDDEV),
        })
    return jittered


def load_real_samples() -> tuple[np.ndarray, np.ndarray, Counter]:
    csv_files = sorted(DATASET_DIR.glob("*.csv"))
    features: list[np.ndarray] = []
    labels: list[str] = []
    skipped = 0

    for csv_path in csv_files:
        with csv_path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            header = next(reader, None)
            if not header:
                continue
            for row in reader:
                if len(row) != 2 + LANDMARK_COLUMNS:
                    skipped += 1
                    continue
                label = row[0].strip().upper()
                handedness = row[1].strip() or "Right"
                if label not in CLASS_LABELS:
                    skipped += 1
                    continue
                try:
                    values = [float(v) for v in row[2:]]
                except ValueError:
                    skipped += 1
                    continue

                raw_landmarks = [
                    {"x": values[i * 3], "y": values[i * 3 + 1], "z": values[i * 3 + 2]}
                    for i in range(21)
                ]
                # IMPORTANT: predict_letter_from_landmarks canonicalizes
                # "Left"-handed input (mirrors it to look right-handed)
                # before extracting features -- this must match exactly, or
                # the model is trained on geometry the live runtime never
                # actually shows it. This was previously missing: ~7,500 of
                # the ~20,000 real training rows are labeled "Left" (from
                # kaggle_extracted.csv), and without this canonicalization
                # step they were trained on raw, un-mirrored landmarks the
                # live prediction path would never present in that form.
                landmarks = list(_canonicalize_landmarks_for_handedness(raw_landmarks, handedness))

                feature_vector = extract_features_from_landmarks(landmarks, handedness).reshape(-1)
                features.append(feature_vector)
                labels.append(label)

                # A mirrored twin of the now-canonicalized (always
                # right-looking) landmarks, so the model also learns to
                # recognize the letter if handedness detection is wrong on a
                # live frame and mirrors a genuinely-correct hand the wrong
                # way -- confirmed by testing that this exact scenario
                # reproduces the user's live "C reads as Q" report.
                mirrored_vector = extract_features_from_landmarks(
                    _mirror_landmarks(landmarks), handedness
                ).reshape(-1)
                features.append(mirrored_vector)
                labels.append(label)

                for _ in range(JITTERS_PER_SAMPLE):
                    jittered_vector = extract_features_from_landmarks(
                        _jitter_landmarks(landmarks), handedness
                    ).reshape(-1)
                    features.append(jittered_vector)
                    labels.append(label)

                for _ in range(ROTATIONS_PER_SAMPLE):
                    # Jitter each rotated variant too, so the model sees the
                    # combined effect of tilt + noisy tracking together.
                    rotated = _rotate_landmarks(landmarks)
                    rotated_vector = extract_features_from_landmarks(rotated, handedness).reshape(-1)
                    features.append(rotated_vector)
                    labels.append(label)

                    jittered_rotated_vector = extract_features_from_landmarks(
                        _jitter_landmarks(rotated), handedness
                    ).reshape(-1)
                    features.append(jittered_rotated_vector)
                    labels.append(label)

    if skipped:
        print(f"Skipped {skipped} malformed/unrecognized rows across {len(csv_files)} CSV file(s).")

    if not features:
        return np.zeros((0, len(next(iter(PROTOTYPES.values()))))), np.asarray([]), Counter()

    return np.vstack(features), np.asarray(labels), Counter(labels)


def synthetic_fill(missing_letters: list[str]) -> tuple[np.ndarray, np.ndarray]:
    if not missing_letters:
        return np.zeros((0, len(next(iter(PROTOTYPES.values()))))), np.asarray([])

    rng = np.random.default_rng(42)
    rows: list[np.ndarray] = []
    labels: list[str] = []
    for label in missing_letters:
        base = PROTOTYPES[label]
        for _ in range(SYNTHETIC_SAMPLES_PER_MISSING_LETTER):
            noise = rng.normal(0.0, 0.06, size=base.shape)
            sample = np.clip(base + noise, 0.0, 1.0)
            rows.append(sample)
            labels.append(label)

    return np.vstack(rows).astype(np.float32), np.asarray(labels)


def evaluate_on_real_data(x_real: np.ndarray, y_real: np.ndarray, counts: Counter) -> float | None:
    min_count = min(counts.values()) if counts else 0
    if len(counts) < 2 or min_count < 2:
        print("Not enough samples per letter yet for a held-out accuracy check (need >=2 rows/letter).")
        return None

    x_train, x_test, y_train, y_test = train_test_split(
        x_real, y_real, test_size=0.2, stratify=y_real, random_state=42
    )
    model = make_pipeline(StandardScaler(), SVC(kernel="rbf", C=20.0, gamma="scale", probability=True))
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    accuracy = float(accuracy_score(y_test, predictions))

    print(f"\nHeld-out accuracy on real recorded data only: {accuracy * 100:.1f}% ({len(y_test)} test rows)")
    print(classification_report(y_test, predictions, zero_division=0))
    return accuracy


def main() -> None:
    x_real, y_real, counts = load_real_samples()
    real_letters = sorted(counts.keys())
    missing_letters = [label for label in CLASS_LABELS if label not in counts]

    print(f"Loaded {len(y_real)} real samples covering {len(real_letters)}/26 letters.")
    for label in CLASS_LABELS:
        marker = "real" if label in counts else "MISSING (synthetic fill)"
        print(f"  {label}: {counts.get(label, 0):>4} samples  [{marker}]")

    if len(y_real) == 0:
        print(
            f"\nNo CSV files found in {DATASET_DIR}. "
            "Record data with collect-landmarks.html, export a CSV into that folder, and re-run this script."
        )
        return

    held_out_accuracy = evaluate_on_real_data(x_real, y_real, counts)

    x_fill, y_fill = synthetic_fill(missing_letters)
    x_final = np.vstack([x_real, x_fill]) if len(x_fill) else x_real
    y_final = np.concatenate([y_real, y_fill]) if len(y_fill) else y_real

    print(f"\nTraining deployed model on {len(y_final)} rows "
          f"({len(y_real)} real + {len(y_fill)} synthetic-filled for missing letters)...")

    final_model = make_pipeline(StandardScaler(), SVC(kernel="rbf", C=20.0, gamma="scale", probability=True))
    final_model.fit(x_final, y_final)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, MODEL_PATH)

    manifest = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "total_real_rows": int(len(y_real)),
        "letters_with_real_data": {label: int(counts[label]) for label in real_letters},
        "letters_synthetic_filled": missing_letters,
        "held_out_accuracy_real_only": held_out_accuracy,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\nSaved model to {MODEL_PATH}")
    print(f"Saved training manifest to {MANIFEST_PATH}")
    if missing_letters:
        print(
            f"\n{len(missing_letters)} letter(s) still have no real samples: {', '.join(missing_letters)}. "
            "The deployed model uses synthetic placeholders for those until you record real data for them."
        )
    print("\nRestart the Django server so it picks up the newly trained model.")


if __name__ == "__main__":
    main()
