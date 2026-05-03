from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Optional, Tuple


_LAST_AI_ERROR = ""

SUPPORTED_WORDS = [
    "HELLO",
    "HOW ARE YOU",
    "WHATS YOUR NAME",
    "COME HERE",
    "COME LETS EAT",
    "EXCUSE",
    "I LOVE YOU",
    "IM SORRY",
    "TRY AGAIN",
    "ARE YOU DEAF OR HEARING",
]

SUPPORTED_ALIASES = {
    "HELLO": "HELLO",
    "HOW ARE YOU": "HOW ARE YOU",
    "WHATS YOUR NAME": "WHATS YOUR NAME",
    "WHATS YOUR NAME": "WHATS YOUR NAME",
    "WHAT'S YOUR NAME": "WHATS YOUR NAME",
    "COME HERE": "COME HERE",
    "COME LETS EAT": "COME LETS EAT",
    "COME LET'S EAT": "COME LETS EAT",
    "EXCUSE": "EXCUSE",
    "I LOVE YOU": "I LOVE YOU",
    "ILOVEYOU": "I LOVE YOU",
    "IM SORRY": "IM SORRY",
    "I'M SORRY": "IM SORRY",
    "TRY AGAIN": "TRY AGAIN",
    "ARE YOU DEAF OR HEARING": "ARE YOU DEAF OR HEARING",
}


def get_last_ai_error() -> str:
    return _LAST_AI_ERROR


def _extract_json(text: str) -> Optional[dict]:
    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _normalize_image_data(image_data: str) -> str:
    if image_data.startswith("data:image"):
        return image_data
    return f"data:image/jpeg;base64,{image_data}"


def _normalize_prediction(prediction: str) -> str:
    return re.sub(r"[^A-Z0-9 ]", "", str(prediction).upper()).strip()


def predict_with_openrouter(image_data: str) -> Optional[Tuple[str, float, bool]]:
    global _LAST_AI_ERROR

    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        _LAST_AI_ERROR = "Missing OPENROUTER_API_KEY"
        return None

    preferred = os.getenv("OPENROUTER_MODEL", "qwen/qwen2.5-vl-72b-instruct:free").strip()
    model_candidates = [
        preferred,
        "qwen/qwen2.5-vl-7b-instruct:free",
        "qwen/qwen2.5-vl-72b-instruct",
    ]
    # Keep order, remove duplicates.
    seen = set()
    models = [m for m in model_candidates if m and not (m in seen or seen.add(m))]

    data_url = _normalize_image_data(image_data)

    for model in models:
        body = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an expert Filipino Sign Language (FSL) interpreter for webcam frames. "
                        "Return strict JSON only. "
                        "If the user is fingerspelling, return exactly one uppercase letter A-Z. "
                        "If the user is signing a word or phrase, return exactly one of these supported labels: "
                        f"{', '.join(SUPPORTED_WORDS)}. "
                        "Do not invent random labels. If uncertain, return prediction NONE and hand_detected false."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Analyze this single webcam frame for FSL. "
                                "Output one of: "
                                "(1) one letter A-Z for fingerspelling, "
                                "(2) one supported word or phrase if a clear word sign is shown, "
                                "(3) NONE if unclear. "
                                "Supported labels are: "
                                f"{', '.join(SUPPORTED_WORDS)}. "
                                "Return strict JSON with keys: prediction (string), confidence (0-100 number), hand_detected (boolean)."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            "temperature": 0.0,
            "max_tokens": 120,
        }

        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://127.0.0.1:8000",
                "X-Title": "kumpas-sign-to-text",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            try:
                detail = err.read().decode("utf-8")
            except Exception:
                detail = str(err)
            _LAST_AI_ERROR = f"HTTP {err.code} on {model}: {detail[:300]}"
            continue
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as err:
            _LAST_AI_ERROR = f"Network/parse error on {model}: {str(err)[:300]}"
            continue

        choices = payload.get("choices", [])
        if not choices:
            _LAST_AI_ERROR = f"No choices returned on {model}"
            continue

        content = choices[0].get("message", {}).get("content", "")
        parsed = _extract_json(content if isinstance(content, str) else str(content))
        if not parsed:
            _LAST_AI_ERROR = f"Invalid JSON content on {model}: {str(content)[:180]}"
            continue

        raw_prediction = str(parsed.get("prediction", "")).strip().upper()
        prediction = SUPPORTED_ALIASES.get(_normalize_prediction(raw_prediction), _normalize_prediction(raw_prediction))
        confidence = float(parsed.get("confidence", 0.0) or 0.0)
        hand_detected = bool(parsed.get("hand_detected", prediction not in {"", "NONE"}))

        if not prediction or prediction == "NONE" or confidence < 35.0:
            _LAST_AI_ERROR = "No confident sign detected"
            return "No hand detected", 0.0, False

        if prediction not in SUPPORTED_WORDS and not (len(prediction) == 1 and prediction.isalpha()):
            _LAST_AI_ERROR = f"Unsupported sign label returned: {prediction}"
            return "No hand detected", 0.0, False

        _LAST_AI_ERROR = ""
        return prediction, max(0.0, min(100.0, confidence)), hand_detected

    return None
