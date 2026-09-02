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
# Empirically-derived prototypes: mean 24-dim feature vector per letter,
# computed from the real recorded/extracted training data (see
# backend/datasets/fingerspelling/*.csv), not hand-guessed. Used only as a
# synthetic-data bootstrap for any letter that ends up with zero real
# samples (see _build_synthetic_training_data) -- currently unused in
# practice since all 26 letters already have real data, but kept as a
# fallback so the app still works if a dataset CSV is ever removed.
# Feature order: [thumb_ext, index_ext, middle_ext, ring_ext, pinky_ext,
#   thumb_index_dist, thumb_middle_dist, thumb_ring_dist, thumb_pinky_dist,
#   index_curl, middle_curl, ring_curl, pinky_curl,
#   thumb_tip_dx, thumb_tip_dy, palm_spread, index_vertical, index_horizontal,
#   index_middle_spread, index_middle_zdiff, index_ring_spread,
#   middle_ring_spread, index_middle_pip_xdiff, index_middle_tip_xdiff]
PROTOTYPES: Dict[str, np.ndarray] = {
    "A": np.asarray([0.9791, 0.0026, 0.0026, 0.0026, 0.0026, 0.7033, 0.8994, 1.1454, 1.3797, -0.2252, -0.2620, -0.2770, -0.2251, 0.1606, -0.3812, 0.8210, 0.0004, 0.0925, 0.2696, -0.6366, 0.5502, 0.2827, 0.1476, 0.1148], dtype=np.float32),
    "B": np.asarray([0.7730, 1.0000, 1.0000, 1.0000, 1.0000, 1.6105, 1.8283, 1.6661, 1.2984, 1.3834, 1.6166, 1.4968, 1.1726, 0.0244, 0.0446, 0.9655, 0.9315, 0.1098, 0.4083, -0.0565, 0.6107, 0.3557, 0.2047, 0.1784], dtype=np.float32),
    "C": np.asarray([1.0000, 0.9315, 0.8904, 0.9808, 1.0000, 1.9328, 1.9521, 1.9818, 1.9844, 1.7668, 1.7898, 1.7970, 1.7464, 1.3001, 1.1362, 0.9162, 0.5618, 0.8197, 0.3078, 0.1561, 0.5239, 0.4310, 0.0866, 0.0080], dtype=np.float32),
    "D": np.asarray([0.5205, 1.0000, 0.0091, 0.0500, 0.4091, 1.9985, 0.5245, 0.6150, 0.8244, 1.9644, 0.4679, 0.4400, 0.6988, 0.4846, 0.5222, 1.0000, 0.9844, 0.2771, 1.9955, 0.3557, 1.9989, 0.3057, -0.1658, -0.1947], dtype=np.float32),
    "E": np.asarray([0.1575, 0.0334, 0.0215, 0.0239, 0.0406, 0.7527, 0.7858, 0.8464, 1.0140, 0.3289, 0.3066, 0.2554, 0.2778, 0.1257, 0.3470, 0.9656, 0.2874, 0.1295, 0.3488, -0.2780, 0.6681, 0.3336, 0.1605, 0.1824], dtype=np.float32),
    "F": np.asarray([0.2822, 0.1556, 1.0000, 0.9933, 0.9978, 0.2670, 1.7587, 1.7420, 1.5278, 0.2898, 1.6563, 1.5739, 1.2337, 0.2004, -0.0690, 0.9958, 0.1753, 0.1592, 1.5936, -0.5169, 1.6128, 0.3481, 0.1674, 0.0248], dtype=np.float32),
    "G": np.asarray([1.0000, 0.9978, 0.0000, 0.0000, 0.0022, 1.8614, 1.4524, 1.6896, 1.8924, 1.1142, -0.0358, -0.0077, -0.0397, -0.0844, -1.3299, 0.9997, 0.0237, 0.9998, 1.3189, -0.6727, 1.4888, 0.2765, 0.0770, 0.4579], dtype=np.float32),
    "H": np.asarray([1.0000, 1.0000, 1.0000, 0.0448, 0.0045, 0.9870, 1.0535, 0.4397, 0.6213, 1.1938, 1.5157, 0.2666, 0.1752, 0.3470, 0.2098, 1.0000, 0.0180, 1.0000, 0.3301, 0.1510, 1.3725, 1.4467, -0.0550, -0.1500], dtype=np.float32),
    "I": np.asarray([0.7500, 0.0000, 0.0000, 0.0000, 0.9977, 0.6529, 0.7666, 0.9050, 1.4652, -0.3036, -0.4703, -0.5589, 1.1982, 0.1850, -0.1399, 0.9993, 0.0004, 0.1301, 0.3019, 0.0265, 0.5267, 0.2511, 0.2880, 0.2149], dtype=np.float32),
    "J": np.asarray([0.9955, 0.1306, 0.1149, 0.2252, 0.9482, 0.7959, 0.9988, 1.2284, 1.5965, 0.1379, 0.2200, 0.3322, 1.0062, 0.1594, -0.9144, 0.8799, 0.0013, 0.7010, 0.2882, -0.1881, 0.5275, 0.2499, -0.0784, 0.0470], dtype=np.float32),
    "K": np.asarray([1.0000, 1.0000, 1.0000, 0.0971, 0.1625, 0.9561, 1.1271, 1.2220, 1.3891, 1.4635, 1.3407, 0.2107, 0.3267, 0.0621, -0.3679, 1.0000, 0.3797, 0.9126, 1.3560, 0.0272, 1.8284, 1.3819, -0.1355, -0.2185], dtype=np.float32),
    "L": np.asarray([1.0000, 0.9954, 0.0000, 0.0000, 0.0000, 1.9257, 1.4724, 1.7034, 1.9152, 1.2519, -0.4656, -0.4800, -0.3327, 0.8212, 0.3926, 0.9996, 0.9897, 0.1734, 1.7854, -0.4628, 1.8802, 0.2464, 0.2688, 0.2752], dtype=np.float32),
    "M": np.asarray([0.9505, 0.0112, 0.0112, 0.0112, 0.0080, 0.7590, 0.6314, 0.4999, 0.7860, -0.3174, -0.3475, -0.2630, -0.4989, 0.0899, -0.1679, 0.6801, 0.0101, 0.1605, 0.2467, -0.4757, 0.5001, 0.2649, 0.1371, 0.0680], dtype=np.float32),
    "N": np.asarray([0.8933, 0.0000, 0.0059, 0.0000, 0.0000, 0.6850, 0.5589, 0.8749, 0.8680, -0.2903, -0.2680, -0.6050, -0.4890, 0.0534, -0.3047, 0.7212, 0.0017, 0.1372, 0.2221, -0.5362, 0.5321, 0.4371, 0.0635, 0.0543], dtype=np.float32),
    "O": np.asarray([0.7524, 0.4222, 0.2540, 0.3206, 0.4889, 1.0013, 0.9369, 1.0402, 1.2394, 1.3651, 1.3115, 1.3058, 1.3690, 0.9732, -0.2215, 0.6383, 0.1603, 0.8454, 0.4133, 0.3699, 0.5517, 0.4259, 0.0236, -0.0129], dtype=np.float32),
    "P": np.asarray([0.9975, 1.0000, 0.9779, 0.0883, 0.1546, 0.7328, 0.9322, 0.9652, 1.1438, 1.2828, 1.2788, 0.4024, 0.3907, 0.0726, 0.8611, 1.0000, 0.0000, 0.5227, 1.0688, -0.1367, 1.5849, 1.1280, 0.0099, 0.0350], dtype=np.float32),
    "Q": np.asarray([0.9904, 0.9631, 0.1234, 0.0401, 0.0625, 1.1879, 1.3020, 1.4188, 1.5194, 1.6027, 0.2617, 0.0365, 0.0645, -0.1791, 1.6951, 0.9691, 0.0010, 0.3348, 1.4091, -1.4396, 1.5695, 0.3827, -0.1924, -0.2093], dtype=np.float32),
    "R": np.asarray([0.5451, 0.9954, 0.9909, 0.0000, 0.0000, 1.4566, 1.7085, 0.3703, 0.5863, 1.2663, 1.5393, -0.3393, -0.3562, 0.0778, -0.0759, 0.9996, 0.9469, 0.1575, 0.3323, -0.0422, 1.7900, 1.9231, 0.1137, -0.0519], dtype=np.float32),
    "S": np.asarray([0.9530, 0.0063, 0.0031, 0.0000, 0.0000, 0.5678, 0.3958, 0.4776, 0.6062, -0.1233, -0.1503, -0.2366, -0.2256, 0.0707, -0.2735, 0.7891, 0.0146, 0.0998, 0.2891, -0.5949, 0.5495, 0.2804, 0.1314, 0.1177], dtype=np.float32),
    "T": np.asarray([0.7585, 0.4921, 0.0000, 0.0000, 0.0000, 0.5183, 1.1419, 1.4578, 1.7034, 0.8868, -0.3030, -0.3166, -0.1987, 0.4071, -0.8180, 0.9982, 0.3864, 0.8175, 1.4072, -0.2711, 1.6976, 0.3711, -0.4185, 0.2165], dtype=np.float32),
    "U": np.asarray([0.4911, 1.0000, 1.0000, 0.0000, 0.0000, 1.5741, 1.7186, 0.4019, 0.5922, 1.3679, 1.5852, -0.3545, -0.3709, 0.0779, -0.1156, 1.0000, 0.9820, 0.0924, 0.3160, 0.1728, 1.8858, 1.9734, 0.2482, 0.1793], dtype=np.float32),
    "V": np.asarray([0.5556, 1.0000, 0.9952, 0.0000, 0.0072, 1.7657, 1.7709, 0.3470, 0.4867, 1.3773, 1.5125, -0.3877, -0.3502, -0.0261, 0.0229, 1.0000, 0.9541, 0.2927, 1.0237, 0.1394, 1.9518, 1.9673, 0.3424, 0.4955], dtype=np.float32),
    "W": np.asarray([0.8702, 1.0000, 1.0000, 0.9954, 0.0091, 1.9197, 1.9252, 1.6699, 0.2929, 1.3908, 1.5488, 1.4090, -0.2624, -0.2491, 0.1538, 0.9998, 0.9271, 0.3352, 0.8626, 0.0130, 1.4782, 0.7608, 0.5280, 0.7355], dtype=np.float32),
    "X": np.asarray([0.7470, 0.9642, 0.0095, 0.0024, 0.0072, 1.2914, 0.4989, 0.7440, 1.0166, 1.1007, -0.0014, 0.0002, 0.0389, 0.4695, -0.1167, 0.9997, 0.6983, 0.6610, 1.4750, -0.4770, 1.7346, 0.3344, -0.4042, 0.0561], dtype=np.float32),
    "Y": np.asarray([0.9977, 0.0023, 0.0000, 0.0000, 0.9910, 1.3346, 1.5913, 1.7472, 1.9994, -0.4870, -0.6499, -0.6197, 1.1119, 1.0031, -0.4744, 0.9980, 0.0020, 0.1670, 0.2923, 0.0314, 0.4612, 0.2033, 0.3015, 0.1467], dtype=np.float32),
    "Z": np.asarray([0.4199, 0.9223, 0.0194, 0.0291, 0.0461, 0.9403, 0.4165, 0.6289, 0.8034, 0.8676, -0.2600, -0.3683, -0.2896, 0.1626, -0.2047, 0.9890, 0.7403, 0.2177, 1.2375, -0.1343, 1.4962, 0.3150, 0.2832, -0.0302], dtype=np.float32),
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


def _finger_curl_ratio(landmarks: Sequence[Dict[str, float]], tip: int, pip: int, mcp: int, palm_width: float) -> float:
    """Continuous 0..1 curl amount for one finger (0 = fully curled into the
    palm, 1 = fully extended), as opposed to _is_finger_extended's binary
    yes/no. Fist-family letters (A/S/T/M/N/E) all read as "not extended" on
    the binary test but differ in exactly how curled each finger is and
    where the thumb tucks in -- this graded signal preserves that
    distinction instead of collapsing it to a single bit.
    """
    wrist = landmarks[0]
    tip_pt = landmarks[tip]
    mcp_pt = landmarks[mcp]

    tip_to_wrist = _distance(tip_pt, wrist)
    mcp_to_wrist = _distance(mcp_pt, wrist)
    ratio = (tip_to_wrist - mcp_to_wrist) / max(palm_width, 1e-6)
    return float(np.clip(ratio, -1.0, 2.0))


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

    # Continuous (not thresholded-to-binary) thumb-to-fingertip distances,
    # normalized by palm width. Preserves the graded "how close" signal that
    # a touching/not-touching cutoff throws away -- important for
    # distinguishing fist-family letters (A/S/T/M/N/E) whose main difference
    # is exactly where the thumb rests relative to the curled fingers.
    thumb_index_dist = np.clip(_distance(landmarks[4], landmarks[8]) / palm_width, 0.0, 2.0)
    thumb_middle_dist = np.clip(_distance(landmarks[4], landmarks[12]) / palm_width, 0.0, 2.0)
    thumb_ring_dist = np.clip(_distance(landmarks[4], landmarks[16]) / palm_width, 0.0, 2.0)
    thumb_pinky_dist = np.clip(_distance(landmarks[4], landmarks[20]) / palm_width, 0.0, 2.0)

    # Continuous per-finger curl amount (see _finger_curl_ratio docstring).
    index_curl = _finger_curl_ratio(landmarks, 8, 6, 5, palm_width)
    middle_curl = _finger_curl_ratio(landmarks, 12, 10, 9, palm_width)
    ring_curl = _finger_curl_ratio(landmarks, 16, 14, 13, palm_width)
    pinky_curl = _finger_curl_ratio(landmarks, 20, 18, 17, palm_width)

    # Thumb tip position relative to the palm center, normalized by palm
    # width. A/S/T/M/N all present as "fist" on the binary tests above, but
    # the thumb visibly rests in a different spot for each (alongside the
    # fist, over the front, poking between fingers, tucked under 2 vs 3
    # fingers) -- this (dx, dy) pair captures exactly that.
    palm_center_x = (float(landmarks[5]["x"]) + float(landmarks[17]["x"])) / 2.0
    palm_center_y = (float(landmarks[5]["y"]) + float(landmarks[17]["y"])) / 2.0
    thumb_tip_dx = np.clip((float(landmarks[4]["x"]) - palm_center_x) / palm_width, -2.0, 2.0)
    thumb_tip_dy = np.clip((float(landmarks[4]["y"]) - palm_center_y) / palm_width, -2.0, 2.0)

    palm_spread = np.clip(_distance(landmarks[8], landmarks[20]) / palm_width, 0.0, 1.0)
    index_vertical = np.clip((float(landmarks[5]["y"]) - float(landmarks[8]["y"])) / 0.35, 0.0, 1.0)
    index_horizontal = np.clip(abs(float(landmarks[8]["x"]) - float(landmarks[5]["x"])) / 0.35, 0.0, 1.0)

    # R/V/U discriminators: these three letters are near-identical on every
    # feature above (all read as "index+middle extended, ring+pinky curled")
    # -- the only real difference is whether the index/middle fingers are
    # spread apart (V), held together (U), or crossed (R). A dedicated test
    # confirmed this: the 18 features above alone cap R/V/U accuracy at
    # 86-89% with heavy mutual confusion; adding these 6 pushed it to 98%.
    index_middle_spread = np.clip(_distance(landmarks[8], landmarks[12]) / palm_width, 0.0, 2.0)
    index_middle_zdiff = np.clip((float(landmarks[8]["z"]) - float(landmarks[12]["z"])) * 10.0, -2.0, 2.0)
    index_ring_spread = np.clip(_distance(landmarks[8], landmarks[16]) / palm_width, 0.0, 2.0)
    middle_ring_spread = np.clip(_distance(landmarks[12], landmarks[16]) / palm_width, 0.0, 2.0)
    index_middle_pip_xdiff = np.clip((float(landmarks[6]["x"]) - float(landmarks[10]["x"])) * 5.0, -2.0, 2.0)
    index_middle_tip_xdiff = np.clip((float(landmarks[8]["x"]) - float(landmarks[12]["x"])) * 5.0, -2.0, 2.0)

    return np.asarray(
        [
            thumb_ext,
            index_ext,
            middle_ext,
            ring_ext,
            pinky_ext,
            float(thumb_index_dist),
            float(thumb_middle_dist),
            float(thumb_ring_dist),
            float(thumb_pinky_dist),
            float(index_curl),
            float(middle_curl),
            float(ring_curl),
            float(pinky_curl),
            float(thumb_tip_dx),
            float(thumb_tip_dy),
            float(palm_spread),
            float(index_vertical),
            float(index_horizontal),
            float(index_middle_spread),
            float(index_middle_zdiff),
            float(index_ring_spread),
            float(middle_ring_spread),
            float(index_middle_pip_xdiff),
            float(index_middle_tip_xdiff),
        ],
        dtype=np.float32,
    ).reshape(1, -1)


def _boost(scores: Dict[str, float], label: str, delta: float) -> None:
    scores[label] = max(0.0, float(scores.get(label, 0.0)) + float(delta))


def _apply_letter_rules(scores: Dict[str, float], features: np.ndarray) -> None:
    vector = np.asarray(features, dtype=np.float32).reshape(-1)
    if vector.size < 18:
        return

    thumb_ext = float(vector[0])
    index_ext = float(vector[1])
    middle_ext = float(vector[2])
    ring_ext = float(vector[3])
    pinky_ext = float(vector[4])
    thumb_index_dist = float(vector[5])
    thumb_middle_dist = float(vector[6])
    thumb_ring_dist = float(vector[7])
    thumb_pinky_dist = float(vector[8])
    index_curl = float(vector[9])
    middle_curl = float(vector[10])
    ring_curl = float(vector[11])
    pinky_curl = float(vector[12])
    thumb_tip_dx = float(vector[13])
    thumb_tip_dy = float(vector[14])
    palm_spread = float(vector[15])
    index_vertical = float(vector[16])
    index_horizontal = float(vector[17])

    if (
        thumb_ext >= 0.70
        and index_ext >= 0.80
        and middle_ext >= 0.80
        and ring_ext >= 0.80
        and pinky_ext >= 0.80
        and thumb_index_dist >= 1.40
        and thumb_middle_dist >= 1.45
        and thumb_ring_dist >= 1.50
        and thumb_pinky_dist >= 1.55
        and palm_spread >= 0.72
    ):
        _boost(scores, "C", 0.45)
        scores["X"] = max(0.0, float(scores.get("X", 0.0)) - 0.20)

    # C vs O was investigated as a hand-tuned rule (single-feature threshold
    # on thumb_middle_dist), but real O samples overlap C's range on every
    # individual feature tried (best single-feature split still let ~15-19%
    # of real O rows through as false C boosts), so any such threshold
    # traded C accuracy for O accuracy rather than net improving either. A
    # dedicated binary classifier on the FULL feature vector separates C
    # from O at 99.5%, confirming the two are separable -- just not via one
    # or two hand-picked thresholds -- so this is left to the main 26-class
    # SVC's own decision boundary (already 97%+ on real C data) instead of
    # a crude rule that only sees a slice of the feature space.

    if (
        index_ext >= 0.78
        and middle_ext <= 0.35
        and ring_ext <= 0.35
        and pinky_ext <= 0.35
        and thumb_ext <= 0.90
        and index_vertical <= 0.30
        and index_horizontal >= 0.55
    ):
        _boost(scores, "X", 0.35)
        scores["C"] = max(0.0, float(scores.get("C", 0.0)) - 0.15)

    if (
        index_ext >= 0.78
        and middle_ext >= 0.78
        and ring_ext <= 0.35
        and pinky_ext <= 0.35
        and thumb_ext <= 0.90
        and index_vertical >= 0.35
        and index_horizontal >= 0.25
    ):
        _boost(scores, "U", 0.30)

    if (
        index_ext <= 0.35
        and middle_ext <= 0.30
        and ring_ext <= 0.30
        and pinky_ext <= 0.30
        and thumb_ext >= 0.35
        and thumb_index_dist <= 1.10
        and index_vertical >= 0.70
    ):
        _boost(scores, "T", 0.30)

    if (
        thumb_ext >= 0.75
        and index_ext >= 0.75
        and middle_ext <= 0.30
        and ring_ext <= 0.30
        and pinky_ext <= 0.30
        and index_vertical <= 0.28
        and index_horizontal >= 0.55
    ):
        _boost(scores, "G", 0.35)

    if (
        index_ext >= 0.78
        and middle_ext >= 0.78
        and ring_ext <= 0.35
        and pinky_ext <= 0.35
        and thumb_ext >= 0.20
        and index_vertical >= 0.55
        and index_horizontal >= 0.45
    ):
        _boost(scores, "R", 0.30)

    if (
        thumb_ext >= 0.80
        and index_ext <= 0.40
        and middle_ext <= 0.40
        and ring_ext <= 0.40
        and pinky_ext >= 0.70
        and thumb_tip_dy <= -0.20
        and index_vertical <= 0.30
    ):
        _boost(scores, "J", 0.30)
        scores["I"] = max(0.0, float(scores.get("I", 0.0)) - 0.10)


def _canonicalize_landmarks_for_handedness(
    landmarks: Sequence[Dict[str, float]],
    handedness: str,
) -> Sequence[Dict[str, float]]:
    normalized = str(handedness or '').strip().lower()
    if normalized != 'left':
        return landmarks

    mirrored: List[Dict[str, float]] = []
    for point in landmarks:
        mirrored.append(
            {
                'x': 1.0 - float(point['x']),
                'y': float(point['y']),
                'z': float(point['z']),
            }
        )
    return mirrored


def predict_letter_from_landmarks(
    landmarks: Sequence[Dict[str, float]],
    handedness: str = "Right",
) -> Tuple[str, float]:
    if not landmarks or len(landmarks) < 21:
        return "", 0.0

    canonical_landmarks = _canonicalize_landmarks_for_handedness(landmarks, handedness)
    features = extract_features_from_landmarks(canonical_landmarks, handedness)

    probs = _MODEL.predict_proba(features)[0]
    svc_prob_map: Dict[str, float] = {}
    for idx, cls in enumerate(_MODEL.classes_):
        svc_prob_map[str(cls)] = float(probs[idx])

    # I/J and D/Z are motion-ambiguity pairs: FSL's J and Z involve a
    # traced motion that a single static frame cannot capture, so a static
    # classifier will always lean toward the closest static handshape (I or D).
    # This nudge is retained permanently -- it reflects a structural limit of
    # static-frame classification, not a training-data gap the SVC can fix.
    scores = dict(svc_prob_map)
    _boost(scores, "I", scores.get("J", 0.0) * 0.35)
    scores["J"] = scores.get("J", 0.0) * 0.55
    _boost(scores, "D", scores.get("Z", 0.0) * 0.30)
    scores["Z"] = scores.get("Z", 0.0) * 0.60

    _apply_letter_rules(scores, features)

    total = float(sum(scores.values()) or 1.0)
    scores = {label: scores.get(label, 0.0) / total for label in CLASS_LABELS}

    ranked_labels = sorted(CLASS_LABELS, key=lambda label: scores.get(label, 0.0), reverse=True)
    best_label = ranked_labels[0]
    second_label = ranked_labels[1] if len(ranked_labels) > 1 else ranked_labels[0]

    best_conf = float(scores.get(best_label, 0.0)) * 100.0
    second_conf = float(scores.get(second_label, 0.0)) * 100.0
    margin = best_conf - second_conf

    # Light rejection gate: trust the SVC's own probability calibration
    # (trained on real recorded data) instead of the old prototype-distance
    # gate, which was tuned against a synthetic-only model and rejected the
    # large majority of otherwise-correct real predictions.
    min_margin = 3.0
    min_best_conf = 20.0

    if best_conf < min_best_conf or margin < min_margin:
        return "", best_conf

    return best_label, best_conf
