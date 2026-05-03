from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import joblib
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


CLASS_LABELS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "fingerspelling_svc.joblib"
PROTOTYPES: Dict[str, np.ndarray] = {
    # [thumb_ext, index_ext, middle_ext, ring_ext, pinky_ext,
    #  thumb_index_touch, thumb_middle_touch, thumb_ring_touch, thumb_pinky_touch,
    #  palm_spread, index_vertical, index_horizontal]
    "A": np.asarray([1, 0, 0, 0, 0, 0, 0, 0, 0, 0.22, 0.25, 0.10], dtype=np.float32),
    "B": np.asarray([0, 1, 1, 1, 1, 0, 0, 0, 0, 0.58, 0.82, 0.08], dtype=np.float32),
    "C": np.asarray([1, 1, 1, 1, 1, 0, 0, 0, 0, 0.34, 0.55, 0.18], dtype=np.float32),
    "D": np.asarray([0, 1, 0, 0, 0, 0, 0, 0, 0, 0.30, 0.88, 0.10], dtype=np.float32),
    "E": np.asarray([0, 0, 0, 0, 0, 1, 1, 1, 1, 0.20, 0.22, 0.10], dtype=np.float32),
    "F": np.asarray([0, 1, 1, 1, 1, 1, 0, 0, 0, 0.40, 0.70, 0.12], dtype=np.float32),
    "G": np.asarray([1, 1, 0, 0, 0, 0, 0, 0, 0, 0.18, 0.35, 0.60], dtype=np.float32),
    "H": np.asarray([0, 1, 1, 0, 0, 0, 0, 0, 0, 0.36, 0.65, 0.46], dtype=np.float32),
    "I": np.asarray([0, 0, 0, 0, 1, 0, 0, 0, 0, 0.24, 0.30, 0.10], dtype=np.float32),
    "J": np.asarray([0, 0, 0, 0, 1, 0, 0, 0, 0, 0.30, 0.34, 0.18], dtype=np.float32),
    "K": np.asarray([1, 1, 1, 0, 0, 0, 0, 0, 0, 0.42, 0.78, 0.26], dtype=np.float32),
    "L": np.asarray([1, 1, 0, 0, 0, 0, 0, 0, 0, 0.36, 0.85, 0.36], dtype=np.float32),
    "M": np.asarray([0, 0, 0, 0, 0, 0, 0, 1, 1, 0.26, 0.22, 0.10], dtype=np.float32),
    "N": np.asarray([0, 0, 0, 0, 0, 0, 1, 1, 0, 0.24, 0.24, 0.10], dtype=np.float32),
    "O": np.asarray([0, 0, 0, 0, 0, 1, 1, 1, 1, 0.16, 0.20, 0.12], dtype=np.float32),
    "P": np.asarray([1, 1, 1, 0, 0, 0, 0, 0, 0, 0.24, 0.45, 0.20], dtype=np.float32),
    "Q": np.asarray([1, 1, 0, 0, 0, 0, 0, 0, 0, 0.12, 0.28, 0.48], dtype=np.float32),
    "R": np.asarray([0, 1, 1, 0, 0, 0, 0, 0, 0, 0.30, 0.78, 0.14], dtype=np.float32),
    "S": np.asarray([0, 0, 0, 0, 0, 0, 0, 0, 0, 0.22, 0.20, 0.10], dtype=np.float32),
    "T": np.asarray([0, 0, 0, 0, 0, 1, 0, 0, 0, 0.20, 0.18, 0.10], dtype=np.float32),
    "U": np.asarray([0, 1, 1, 0, 0, 0, 0, 0, 0, 0.28, 0.83, 0.16], dtype=np.float32),
    "V": np.asarray([0, 1, 1, 0, 0, 0, 0, 0, 0, 0.42, 0.86, 0.28], dtype=np.float32),
    "W": np.asarray([0, 1, 1, 1, 0, 0, 0, 0, 0, 0.46, 0.85, 0.34], dtype=np.float32),
    "X": np.asarray([0, 1, 0, 0, 0, 0, 0, 0, 0, 0.22, 0.62, 0.12], dtype=np.float32),
    "Y": np.asarray([1, 0, 0, 0, 1, 0, 0, 0, 0, 0.40, 0.28, 0.28], dtype=np.float32),
    "Z": np.asarray([0, 1, 0, 0, 0, 0, 0, 0, 0, 0.27, 0.60, 0.26], dtype=np.float32),
}


def _build_synthetic_training_data() -> Tuple[np.ndarray, np.ndarray]:
    rows: List[np.ndarray] = []
    labels: List[str] = []
    rng = np.random.default_rng(42)

    for label, base in PROTOTYPES.items():
        for _ in range(240):
            noise = rng.normal(0.0, 0.06, size=base.shape)
            sample = np.clip(base + noise, 0.0, 1.0)
            rows.append(sample)
            labels.append(label)

    x_train = np.vstack(rows).astype(np.float32)
    y_train = np.asarray(labels)
    return x_train, y_train


def _train_model() -> SVC:
    x_train, y_train = _build_synthetic_training_data()
    model = make_pipeline(
        StandardScaler(),
        SVC(kernel="rbf", C=5.0, gamma="scale", probability=True),
    )
    model.fit(x_train, y_train)
    return model


def _load_or_build_model() -> SVC:
    if MODEL_PATH.exists():
        try:
            loaded = joblib.load(MODEL_PATH)
            classes = set(str(c) for c in getattr(loaded, "classes_", []))
            expected = set(CLASS_LABELS)
            n_features = None
            try:
                svc = loaded.named_steps.get("svc") if hasattr(loaded, "named_steps") else None
                n_features = int(getattr(svc, "n_features_in_", 0)) if svc is not None else None
            except Exception:
                n_features = None

            if classes == expected and n_features == len(next(iter(PROTOTYPES.values()))):
                return loaded
        except Exception:
            pass

    model = _train_model()
    try:
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, MODEL_PATH)
    except Exception:
        # Non-fatal: model can still run in-memory.
        pass
    return model


_MODEL = _load_or_build_model()


def _distance(a: Dict[str, float], b: Dict[str, float]) -> float:
    dx = float(a["x"]) - float(b["x"])
    dy = float(a["y"]) - float(b["y"])
    return float(np.sqrt((dx * dx) + (dy * dy)))


def _vector(a: Dict[str, float], b: Dict[str, float]) -> np.ndarray:
    return np.asarray([float(b["x"]) - float(a["x"]), float(b["y"]) - float(a["y"])], dtype=np.float32)


def _cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    n1 = float(np.linalg.norm(v1))
    n2 = float(np.linalg.norm(v2))
    if n1 <= 1e-6 or n2 <= 1e-6:
        return 0.0
    return float(np.dot(v1, v2) / (n1 * n2))


def _is_finger_extended(landmarks: Sequence[Dict[str, float]], tip: int, pip: int, mcp: int) -> float:
    wrist = landmarks[0]
    tip_pt = landmarks[tip]
    pip_pt = landmarks[pip]
    mcp_pt = landmarks[mcp]

    tip_to_wrist = _distance(tip_pt, wrist)
    pip_to_wrist = _distance(pip_pt, wrist)
    mcp_to_wrist = _distance(mcp_pt, wrist)

    seg1 = _vector(pip_pt, tip_pt)
    seg2 = _vector(mcp_pt, pip_pt)
    straightness = _cosine_similarity(seg1, seg2)

    # Orientation-robust extension rule:
    # tip should be farther from wrist than joints, and the finger chain should be relatively straight.
    is_farther = tip_to_wrist > (pip_to_wrist + 0.01) and tip_to_wrist > (mcp_to_wrist + 0.02)
    is_straight = straightness > 0.2
    return 1.0 if (is_farther and is_straight) else 0.0


def _is_thumb_extended(landmarks: Sequence[Dict[str, float]], handedness: str) -> float:
    # Handedness is kept for API compatibility, but the geometric test below is side-agnostic.
    _ = handedness

    thumb_tip = landmarks[4]
    thumb_ip = landmarks[3]
    thumb_mcp = landmarks[2]
    index_mcp = landmarks[5]

    tip_to_index_mcp = _distance(thumb_tip, index_mcp)
    ip_to_index_mcp = _distance(thumb_ip, index_mcp)

    seg1 = _vector(thumb_ip, thumb_tip)
    seg2 = _vector(thumb_mcp, thumb_ip)
    straightness = _cosine_similarity(seg1, seg2)

    is_farther = tip_to_index_mcp > (ip_to_index_mcp + 0.01)
    is_straight = straightness > 0.1
    return 1.0 if (is_farther and is_straight) else 0.0


def extract_features_from_landmarks(landmarks: Sequence[Dict[str, float]], handedness: str) -> np.ndarray:
    thumb_ext = _is_thumb_extended(landmarks, handedness)
    index_ext = _is_finger_extended(landmarks, 8, 6, 5)
    middle_ext = _is_finger_extended(landmarks, 12, 10, 9)
    ring_ext = _is_finger_extended(landmarks, 16, 14, 13)
    pinky_ext = _is_finger_extended(landmarks, 20, 18, 17)

    palm_width = max(_distance(landmarks[5], landmarks[17]), 1e-6)
    # Adaptive touch threshold helps curled-finger signs like E under varied camera distance.
    base_touch_threshold = float(np.clip(palm_width * 0.34, 0.045, 0.085))

    thumb_index_dist = _distance(landmarks[4], landmarks[8])
    thumb_index_touch = 1.0 if thumb_index_dist < base_touch_threshold else 0.0
    thumb_middle_touch = 1.0 if _distance(landmarks[4], landmarks[12]) < (base_touch_threshold + 0.008) else 0.0
    thumb_ring_touch = 1.0 if _distance(landmarks[4], landmarks[16]) < (base_touch_threshold + 0.010) else 0.0
    thumb_pinky_touch = 1.0 if _distance(landmarks[4], landmarks[20]) < (base_touch_threshold + 0.012) else 0.0

    palm_spread = np.clip(_distance(landmarks[8], landmarks[20]) / palm_width, 0.0, 1.0)
    index_vertical = np.clip((float(landmarks[5]["y"]) - float(landmarks[8]["y"])) / 0.35, 0.0, 1.0)
    index_horizontal = np.clip(abs(float(landmarks[8]["x"]) - float(landmarks[5]["x"])) / 0.35, 0.0, 1.0)

    return np.asarray(
        [
            thumb_ext,
            index_ext,
            middle_ext,
            ring_ext,
            pinky_ext,
            thumb_index_touch,
            thumb_middle_touch,
            thumb_ring_touch,
            thumb_pinky_touch,
            float(palm_spread),
            float(index_vertical),
            float(index_horizontal),
        ],
        dtype=np.float32,
    ).reshape(1, -1)


def _heuristic_letter_from_features(features: np.ndarray) -> Tuple[str, float]:
    vals = features.reshape(-1)
    (
        thumb_ext,
        index_ext,
        middle_ext,
        ring_ext,
        pinky_ext,
        thumb_index_touch,
        thumb_middle_touch,
        thumb_ring_touch,
        thumb_pinky_touch,
        palm_spread,
        index_vertical,
        index_horizontal,
    ) = [float(v) for v in vals]

    t = thumb_ext >= 0.5
    i = index_ext >= 0.5
    m = middle_ext >= 0.5
    r = ring_ext >= 0.5
    p = pinky_ext >= 0.5
    touch_index = thumb_index_touch >= 0.5
    touch_count = thumb_index_touch + thumb_middle_touch + thumb_ring_touch + thumb_pinky_touch
    touch_many = (thumb_middle_touch + thumb_ring_touch + thumb_pinky_touch) >= 1.5

    if t and (not i) and (not m) and (not r) and (not p):
        return "A", 96.0
    if (not t) and i and m and r and p and (not touch_index) and palm_spread >= 0.42:
        return "B", 96.0
    if (not t) and i and (not m) and (not r) and (not p) and index_vertical >= 0.7:
        return "D", 95.0
    if (not t) and (not i) and (not m) and (not r) and p:
        return "I", 95.0
    if t and i and (not m) and (not r) and (not p):
        return "L", 95.0
    if (not t) and i and m and r and (not p):
        return "W", 95.0
    if t and (not i) and (not m) and (not r) and p:
        return "Y", 95.0
    if touch_index and i and m and r and p:
        return "F", 92.0
    # Strong E signature: fist with multiple thumb-finger contacts.
    if (not t) and (not i) and (not m) and (not r) and (not p) and touch_count >= 2.5:
        return "E", 96.0
    if (not i) and (not m) and (not r) and (not p) and touch_many:
        return "E", 90.0
    if (not i) and (not m) and (not r) and (not p) and touch_index and touch_count <= 1.5:
        return "T", 88.0

    return "", 0.0


def _nearest_prototype_distance(features: np.ndarray, label: str) -> float:
    proto = PROTOTYPES.get(label)
    if proto is None:
        return 999.0
    vals = features.reshape(-1).astype(np.float32)
    return float(np.linalg.norm(vals - proto))


def _prototype_probabilities(features: np.ndarray) -> Dict[str, float]:
    vals = features.reshape(-1).astype(np.float32)
    weights: Dict[str, float] = {}

    for label in CLASS_LABELS:
        proto = PROTOTYPES.get(label)
        if proto is None:
            continue
        dist = float(np.linalg.norm(vals - proto))
        # Inverse-distance weighting. Smaller distance => higher probability mass.
        weights[label] = 1.0 / max(dist, 1e-4)

    total = float(sum(weights.values()) or 1.0)
    return {label: (weights.get(label, 0.0) / total) for label in CLASS_LABELS}


def _landmark_metrics(landmarks: Sequence[Dict[str, float]]) -> Dict[str, float]:
    palm_width = max(_distance(landmarks[5], landmarks[17]), 1e-6)

    x8 = float(landmarks[8]["x"])
    x12 = float(landmarks[12]["x"])
    x6 = float(landmarks[6]["x"])
    x10 = float(landmarks[10]["x"])

    return {
        "index_middle_tip_sep": _distance(landmarks[8], landmarks[12]) / palm_width,
        "middle_ring_tip_sep": _distance(landmarks[12], landmarks[16]) / palm_width,
        "ring_pinky_tip_sep": _distance(landmarks[16], landmarks[20]) / palm_width,
        "thumb_to_index_mcp": _distance(landmarks[4], landmarks[5]) / palm_width,
        "thumb_to_middle_mcp": _distance(landmarks[4], landmarks[9]) / palm_width,
        "thumb_to_ring_mcp": _distance(landmarks[4], landmarks[13]) / palm_width,
        "thumb_to_pinky_mcp": _distance(landmarks[4], landmarks[17]) / palm_width,
        "index_cross_middle": 1.0 if ((x8 - x12) * (x6 - x10) < 0.0) else 0.0,
        "index_vertical": np.clip((float(landmarks[5]["y"]) - float(landmarks[8]["y"])) / 0.35, 0.0, 1.0),
        "index_horizontal": np.clip(abs(float(landmarks[8]["x"]) - float(landmarks[5]["x"])) / 0.35, 0.0, 1.0),
    }


def _boost(scores: Dict[str, float], label: str, delta: float) -> None:
    scores[label] = max(0.0, float(scores.get(label, 0.0)) + float(delta))


def _apply_confusion_rules(
    scores: Dict[str, float],
    features: np.ndarray,
    landmarks: Sequence[Dict[str, float]],
) -> Dict[str, float]:
    vals = features.reshape(-1)
    thumb_ext, index_ext, middle_ext, ring_ext, pinky_ext = [float(v) for v in vals[:5]]
    thumb_index_touch, thumb_middle_touch, thumb_ring_touch, thumb_pinky_touch = [float(v) for v in vals[5:9]]
    palm_spread = float(vals[9])
    metrics = _landmark_metrics(landmarks)

    t = thumb_ext >= 0.5
    i = index_ext >= 0.5
    m = middle_ext >= 0.5
    r = ring_ext >= 0.5
    p = pinky_ext >= 0.5

    # I/J and D/Z are motion-sensitive pairs; static frames should prefer I and D.
    _boost(scores, "I", scores.get("J", 0.0) * 0.35)
    scores["J"] = scores.get("J", 0.0) * 0.55
    _boost(scores, "D", scores.get("Z", 0.0) * 0.30)
    scores["Z"] = scores.get("Z", 0.0) * 0.60

    # U vs V vs R
    if i and m and (not r) and (not p):
        sep = float(metrics["index_middle_tip_sep"])
        crossed = float(metrics["index_cross_middle"])
        if crossed > 0.5:
            _boost(scores, "R", 0.12)
            _boost(scores, "U", -0.04)
            _boost(scores, "V", -0.04)
        elif sep >= 0.22:
            _boost(scores, "V", 0.12)
            _boost(scores, "U", -0.03)
            _boost(scores, "R", -0.03)
        elif sep <= 0.13:
            _boost(scores, "U", 0.10)
            _boost(scores, "V", -0.03)

    # A / S / T / M / N are fist-family and often confused.
    fist = (not i) and (not m) and (not r) and (not p)
    if fist:
        thumb_mcp_distances = {
            "index": float(metrics["thumb_to_index_mcp"]),
            "middle": float(metrics["thumb_to_middle_mcp"]),
            "ring": float(metrics["thumb_to_ring_mcp"]),
            "pinky": float(metrics["thumb_to_pinky_mcp"]),
        }
        nearest = min(thumb_mcp_distances, key=thumb_mcp_distances.get)
        touch_count = float(thumb_index_touch + thumb_middle_touch + thumb_ring_touch + thumb_pinky_touch)

        if t:
            _boost(scores, "A", 0.12)
            _boost(scores, "S", -0.04)
        else:
            _boost(scores, "S", 0.08)

        if thumb_index_touch >= 0.5:
            _boost(scores, "T", 0.10)

        if nearest in {"ring", "pinky"} or (thumb_ring_touch + thumb_pinky_touch) >= 1.5:
            _boost(scores, "M", 0.11)
        elif nearest in {"middle", "ring"} or (thumb_middle_touch + thumb_ring_touch) >= 1.5:
            _boost(scores, "N", 0.10)

        # E is frequently confused with S/T/M/N in static webcam frames.
        # Favor E when the thumb touches multiple fingertips and palm is compact.
        if (not t) and touch_count >= 2.5:
            _boost(scores, "E", 0.14)
            _boost(scores, "S", -0.03)
            if thumb_index_touch >= 0.5:
                _boost(scores, "T", -0.03)
        if (not t) and touch_count >= 2.0 and palm_spread <= 0.26:
            _boost(scores, "E", 0.08)
        if (not t) and palm_spread <= 0.30 and float(metrics["thumb_to_middle_mcp"]) <= 0.52:
            _boost(scores, "E", 0.07)
        if (not t) and palm_spread <= 0.28 and float(metrics["thumb_to_ring_mcp"]) <= 0.58:
            _boost(scores, "E", 0.06)

    # C vs O
    if i and m and r and p:
        if (thumb_index_touch + thumb_middle_touch + thumb_ring_touch + thumb_pinky_touch) >= 2.0:
            _boost(scores, "O", 0.10)
            _boost(scores, "C", -0.03)
        elif palm_spread >= 0.30:
            _boost(scores, "C", 0.09)

    # G vs Q (both index/thumb prominent, differ by direction)
    if t and i and (not m) and (not r) and (not p):
        if float(metrics["index_horizontal"]) > float(metrics["index_vertical"]):
            _boost(scores, "G", 0.10)
            _boost(scores, "Q", -0.02)
        else:
            _boost(scores, "Q", 0.08)

    total = float(sum(max(0.0, value) for value in scores.values()) or 1.0)
    return {label: max(0.0, float(scores.get(label, 0.0))) / total for label in CLASS_LABELS}


def predict_letter_from_landmarks(
    landmarks: Sequence[Dict[str, float]],
    handedness: str = "Right",
) -> Tuple[str, float]:
    if not landmarks or len(landmarks) < 21:
        return "", 0.0

    features = extract_features_from_landmarks(landmarks, handedness)
    vals = features.reshape(-1)
    thumb_ext, index_ext, middle_ext, ring_ext, pinky_ext = [float(v) for v in vals[:5]]
    thumb_index_touch, thumb_middle_touch, thumb_ring_touch, thumb_pinky_touch = [float(v) for v in vals[5:9]]
    palm_spread = float(vals[9])

    # Deterministic guardrail for persistent E misses.
    # If all non-thumb fingers are curled and thumb is contacting multiple fingertips,
    # return E directly before probabilistic blending can pull it to S/T/M/N.
    e_touch_count = thumb_index_touch + thumb_middle_touch + thumb_ring_touch + thumb_pinky_touch
    if (
        thumb_ext < 0.5
        and index_ext < 0.5
        and middle_ext < 0.5
        and ring_ext < 0.5
        and pinky_ext < 0.5
        and e_touch_count >= 2.5
        and palm_spread <= 0.36
    ):
        return "E", 96.0

    heuristic_label, heuristic_conf = _heuristic_letter_from_features(features)

    probs = _MODEL.predict_proba(features)[0]
    svc_prob_map: Dict[str, float] = {}
    for idx, cls in enumerate(_MODEL.classes_):
        svc_prob_map[str(cls)] = float(probs[idx])

    proto_prob_map = _prototype_probabilities(features)

    # Blend ML classifier with prototype similarity to improve stability on FSL hand shapes.
    blended: Dict[str, float] = {}
    for label in CLASS_LABELS:
        svc_part = svc_prob_map.get(label, 0.0)
        proto_part = proto_prob_map.get(label, 0.0)
        blended[label] = (0.62 * svc_part) + (0.38 * proto_part)

    # Heuristics should help ranking, not hard-force a letter.
    if heuristic_label in blended:
        heuristic_boost = 0.02
        # A is a common false positive when non-thumb fingers are underestimated.
        if heuristic_label == "A":
            heuristic_boost = 0.008
        elif heuristic_label == "E":
            heuristic_boost = 0.10
        blended[heuristic_label] = float(blended.get(heuristic_label, 0.0)) + heuristic_boost

    blended = _apply_confusion_rules(blended, features, landmarks)

    ranked_labels = sorted(CLASS_LABELS, key=lambda label: blended.get(label, 0.0), reverse=True)
    best_label = ranked_labels[0]
    second_label = ranked_labels[1] if len(ranked_labels) > 1 else ranked_labels[0]

    best_conf = float(blended.get(best_label, 0.0)) * 100.0
    second_conf = float(blended.get(second_label, 0.0)) * 100.0
    margin = best_conf - second_conf
    proto_distance = _nearest_prototype_distance(features, best_label)

    if best_label not in CLASS_LABELS:
        return "", best_conf

    # Precision-first but less over-rejection than before.
    min_margin = 2.0
    max_proto_distance = 0.68
    min_best_conf = 14.0

    # E commonly shares geometry with fist-family letters, so allow slightly
    # softer acceptance gates for E to avoid frequent dropouts.
    if best_label == "E":
        min_margin = 0.8
        max_proto_distance = 0.82
        min_best_conf = 10.5

    if best_conf < min_best_conf or margin < min_margin or proto_distance > max_proto_distance:
        # Soft fallback for realtime usability: if a hand is present and the model has a
        # somewhat plausible top class, emit the candidate with lower confidence.
        if best_conf >= 7.0 and proto_distance <= 0.90:
            return best_label, best_conf
        return "", best_conf

    return best_label, best_conf
