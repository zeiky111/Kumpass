from typing import Tuple

try:
    import cv2
except Exception:
    cv2 = None

try:
    import numpy as np
except Exception:
    np = None

_PREV_FRAME_SMALL = None


def predict_from_image_bytes(image_bytes: bytes) -> Tuple[str, float, bool]:
    global _PREV_FRAME_SMALL

    if not image_bytes:
        return "No hand detected", 0.0, False

    if cv2 is None or np is None:
        return "No hand detected", 0.0, False

    frame_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image_bgr = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
    if image_bgr is None:
        return "No hand detected", 0.0, False

    # Motion gating: avoid prediction while scene is mostly static.
    gray_small = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray_small = cv2.resize(gray_small, (96, 96))
    motion_score = 0.0
    if _PREV_FRAME_SMALL is not None:
        diff = cv2.absdiff(gray_small, _PREV_FRAME_SMALL)
        motion_score = float(np.mean(diff))
    _PREV_FRAME_SMALL = gray_small

    # Skin-color gating: rough hand-presence heuristic.
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    lower1 = np.array([0, 25, 60], dtype=np.uint8)
    upper1 = np.array([20, 190, 255], dtype=np.uint8)
    lower2 = np.array([160, 25, 60], dtype=np.uint8)
    upper2 = np.array([180, 190, 255], dtype=np.uint8)
    mask1 = cv2.inRange(hsv, lower1, upper1)
    mask2 = cv2.inRange(hsv, lower2, upper2)
    skin_mask = cv2.bitwise_or(mask1, mask2)
    skin_ratio = float(cv2.countNonZero(skin_mask)) / float(skin_mask.size)

    hand_detected = motion_score >= 3.0 and skin_ratio >= 0.02
    if not hand_detected:
        return "No hand detected", 0.0, False

    # No static dictionary fallback: return hand presence only when AI provider is unavailable.
    return "No hand detected", 0.0, False
