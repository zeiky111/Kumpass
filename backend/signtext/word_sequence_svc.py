"""Local classifier for word/phrase signs from a short two-hand MediaPipe landmark sequence.

Unlike fingerspelling (a single static hand shape), a word/phrase sign is a
short gesture performed over roughly 1-3 seconds, and many FSL words use
both hands. This module turns a variable-length sequence of per-frame hand
records into a fixed-length feature vector (start shape, end shape,
per-landmark motion range, wrist trajectory -- per hand slot) and classifies
it with a StandardScaler+SVC pipeline, mirroring the pattern used for
fingerspelling.

Each frame is a dict with explicit left/right hand slots (not index-order,
since MediaPipe does not guarantee stable hand ordering across frames):
    {"left": [[x, y, z]] * 21 | None, "right": [[x, y, z]] * 21 | None}

There is no synthetic fallback here: word gestures can't be reasonably
hand-guessed the way static letter shapes can. Until a real model has been
trained (see backend/scripts/train_word_model.py), predict_word_from_sequence
simply returns ("", 0.0), so callers should keep using whatever fallback
(e.g. the cloud AI hybrid) they already have.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import joblib
import numpy as np

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "word_sequence_svc.joblib"
MIN_FRAMES = 4
HAND_SLOTS = ("left", "right")
LANDMARKS_PER_HAND = 21
COORDS_PER_LANDMARK = 3
HAND_DIM = LANDMARKS_PER_HAND * COORDS_PER_LANDMARK  # 63

_MODEL = None
_MODEL_LOAD_ATTEMPTED = False


def _get_model():
    global _MODEL, _MODEL_LOAD_ATTEMPTED
    if _MODEL_LOAD_ATTEMPTED:
        return _MODEL

    _MODEL_LOAD_ATTEMPTED = True
    if MODEL_PATH.exists():
        try:
            _MODEL = joblib.load(MODEL_PATH)
        except Exception:
            _MODEL = None
    return _MODEL


def _hand_array(frame: Dict[str, Optional[Sequence[Sequence[float]]]], slot: str) -> Tuple[np.ndarray, bool]:
    """Returns (63-dim flattened landmarks, present flag) for one hand slot in one frame."""
    raw = frame.get(slot) if isinstance(frame, dict) else None
    if raw is None:
        return np.zeros(HAND_DIM, dtype=np.float32), False
    try:
        arr = np.asarray(raw, dtype=np.float32)
    except Exception:
        return np.zeros(HAND_DIM, dtype=np.float32), False
    if arr.shape != (LANDMARKS_PER_HAND, COORDS_PER_LANDMARK):
        return np.zeros(HAND_DIM, dtype=np.float32), False
    return arr.reshape(-1), True


def extract_sequence_features(
    frames: Sequence[Dict[str, Optional[Sequence[Sequence[float]]]]],
) -> Optional[np.ndarray]:
    """frames: list of per-frame dicts, each {"left": [[x,y,z]]*21 | None, "right": [...] | None}."""

    if not frames or len(frames) < MIN_FRAMES:
        return None

    n_frames = len(frames)
    # per_hand[slot] -> (n_frames, 63) landmark array
    # present[slot]  -> (n_frames,) boolean presence mask
    per_hand: Dict[str, np.ndarray] = {}
    present: Dict[str, np.ndarray] = {}

    for slot in HAND_SLOTS:
        rows: List[np.ndarray] = []
        presence: List[bool] = []
        for frame in frames:
            vec, is_present = _hand_array(frame, slot)
            rows.append(vec)
            presence.append(is_present)
        per_hand[slot] = np.vstack(rows).astype(np.float32)
        present[slot] = np.asarray(presence, dtype=bool)

    if not (present["left"].any() or present["right"].any()):
        return None

    parts: List[np.ndarray] = []

    for slot in HAND_SLOTS:
        arr = per_hand[slot]  # (n_frames, 63)
        mask = present[slot]
        if mask.any():
            present_arr = arr[mask]
            first_frame = present_arr[0]
            last_frame = present_arr[-1]
            per_landmark_range = present_arr.max(axis=0) - present_arr.min(axis=0)
            per_landmark_mean = present_arr.mean(axis=0)

            wrist_path = present_arr.reshape(-1, LANDMARKS_PER_HAND, COORDS_PER_LANDMARK)[:, 0, :]
            displacement = wrist_path[-1] - wrist_path[0]
            frame_deltas = np.diff(wrist_path, axis=0)
            path_length = float(np.sum(np.linalg.norm(frame_deltas, axis=1))) if len(frame_deltas) else 0.0
        else:
            first_frame = np.zeros(HAND_DIM, dtype=np.float32)
            last_frame = np.zeros(HAND_DIM, dtype=np.float32)
            per_landmark_range = np.zeros(HAND_DIM, dtype=np.float32)
            per_landmark_mean = np.zeros(HAND_DIM, dtype=np.float32)
            displacement = np.zeros(3, dtype=np.float32)
            path_length = 0.0

        presence_fraction = float(mask.mean())

        parts.append(first_frame)
        parts.append(last_frame)
        parts.append(per_landmark_range)
        parts.append(per_landmark_mean)
        parts.append(np.asarray(
            [displacement[0], displacement[1], displacement[2], path_length, float(n_frames), presence_fraction],
            dtype=np.float32,
        ))

    # Two-hand relative feature: distance between left/right wrists across
    # frames where both hands are present (captures interacting two-hand signs).
    both_present = present["left"] & present["right"]
    if both_present.any():
        left_wrist = per_hand["left"].reshape(-1, LANDMARKS_PER_HAND, COORDS_PER_LANDMARK)[both_present, 0, :]
        right_wrist = per_hand["right"].reshape(-1, LANDMARKS_PER_HAND, COORDS_PER_LANDMARK)[both_present, 0, :]
        wrist_dist = np.linalg.norm(left_wrist - right_wrist, axis=1)
        both_hands_extra = np.asarray([float(wrist_dist.mean()), float(wrist_dist.max() - wrist_dist.min())], dtype=np.float32)
    else:
        both_hands_extra = np.zeros(2, dtype=np.float32)

    parts.append(both_hands_extra)

    return np.concatenate(parts).reshape(1, -1)


def predict_word_from_sequence(
    frames: Sequence[Dict[str, Optional[Sequence[Sequence[float]]]]],
) -> Tuple[str, float]:
    model = _get_model()
    if model is None:
        return "", 0.0

    features = extract_sequence_features(frames)
    if features is None:
        return "", 0.0

    try:
        probs = model.predict_proba(features)[0]
    except Exception:
        return "", 0.0

    classes = list(getattr(model, "classes_", []))
    if not classes:
        return "", 0.0

    best_idx = int(np.argmax(probs))
    best_label = str(classes[best_idx])
    best_conf = float(probs[best_idx]) * 100.0
    return best_label, best_conf
