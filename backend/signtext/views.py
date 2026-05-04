import base64
import os
import random
from typing import Any
from django.db import DatabaseError, OperationalError
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils.text import slugify

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .ai_word_inference import get_last_ai_error, predict_with_openrouter
from .fingerspelling_svc import predict_letter_from_landmarks
from .inference import predict_from_image_bytes
from .models import Announcement, LearningModule, ModuleFile, SignPredictionLog, UserLearningState, UserProfile
from .serializers import (
    AnnouncementSerializer,
    LearningModuleSerializer,
    LearningStateSerializer,
    LoginSerializer,
    ModuleFileSerializer,
    SignPredictionLogSerializer,
    SignupSerializer,
)


@api_view(["GET"])
def health_check(request: Any) -> Response:
    return Response({"status": "ok", "service": "kumpas-signtext-api"})


@api_view(["POST"])
def predict_sign(request: Any) -> Response:
    image_data = request.data.get("image", "")
    source = request.data.get("source", "camera")

    if not image_data or not isinstance(image_data, str):
        return Response({"error": "Missing image field"}, status=400)

    ai_prediction = predict_with_openrouter(image_data)
    ai_available = ai_prediction is not None

    # Accept both plain base64 and data URLs.
    if "," in image_data:
        image_data = image_data.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(image_data)
    except Exception:
        return Response({"error": "Invalid base64 image"}, status=400)

    if ai_available:
        prediction, confidence, hand_detected = ai_prediction
    else:
        prediction, confidence, hand_detected = predict_from_image_bytes(image_bytes)

    log_id = None
    if hand_detected:
        log = SignPredictionLog.objects.create(
            prediction=prediction,
            confidence=round(confidence, 2),
            source=source,
        )
        log_id = log.id

    return Response(
        {
            "id": log_id,
            "prediction": prediction,
            "confidence": round(confidence, 2),
            "hand_detected": hand_detected,
            "ai_available": ai_available,
            "ai_error": "" if ai_available else get_last_ai_error(),
        }
    )


@api_view(["GET"])
def recent_predictions(request: Any) -> Response:
    logs = SignPredictionLog.objects.all()[:20]
    serializer = SignPredictionLogSerializer(logs, many=True)
    return Response(serializer.data)


@api_view(["POST"])
def predict_fingerspelling(request: Any) -> Response:
    landmarks = request.data.get("landmarks", [])
    handedness = request.data.get("handedness", "Right")
    image_data = request.data.get("image", "")
    use_ai = bool(request.data.get("use_ai", False))

    if not isinstance(landmarks, list):
        return Response({"error": "landmarks must be a list"}, status=400)

    svc_letter, svc_confidence = predict_letter_from_landmarks(landmarks, handedness)

    # Keep realtime fingerspelling snappy: commit fast SVC result immediately.
    if svc_letter and float(svc_confidence) >= 7.0:
        return Response(
            {
                "letter": svc_letter,
                "confidence": round(float(svc_confidence), 2),
                "hand_detected": bool(landmarks),
                "svc_letter": svc_letter,
                "svc_confidence": round(float(svc_confidence), 2),
                "ai_letter": "",
                "ai_confidence": 0.0,
                "ai_available": False,
                "ai_error": "skipped_for_latency",
            }
        )

    ai_letter = ""
    ai_confidence = 0.0
    ai_available = False
    ai_error = ""
    hand_detected = bool(landmarks)

    ai_key_present = bool(os.getenv("OPENROUTER_API_KEY", "").strip())
    if use_ai and ai_key_present and isinstance(image_data, str) and image_data.strip():
        ai_prediction = predict_with_openrouter(image_data)
        ai_available = ai_prediction is not None
        if ai_prediction is not None:
            ai_pred_label, ai_pred_conf, ai_hand_detected = ai_prediction
            ai_pred_label = str(ai_pred_label or "").strip().upper()
            if len(ai_pred_label) == 1 and ai_pred_label.isalpha() and ai_pred_conf >= 35:
                ai_letter = ai_pred_label
                ai_confidence = float(ai_pred_conf)
            hand_detected = hand_detected or bool(ai_hand_detected)
        else:
            ai_error = get_last_ai_error()

    final_letter = svc_letter
    final_confidence = float(svc_confidence)

    if svc_letter and ai_letter:
        if svc_letter == ai_letter:
            final_letter = svc_letter
            final_confidence = min(99.0, (0.6 * float(svc_confidence)) + (0.4 * float(ai_confidence)) + 4.0)
        else:
            # If both models disagree and confidence gap is small, avoid forcing a wrong letter.
            gap = abs(float(svc_confidence) - float(ai_confidence))
            if gap < 10.0:
                final_letter = ""
                final_confidence = max(float(svc_confidence), float(ai_confidence))
            elif float(svc_confidence) > float(ai_confidence):
                final_letter = svc_letter
                final_confidence = float(svc_confidence)
            else:
                final_letter = ai_letter
                final_confidence = float(ai_confidence)
    elif ai_letter and not svc_letter:
        if float(ai_confidence) >= 68.0:
            final_letter = ai_letter
            final_confidence = float(ai_confidence)
    elif not svc_letter:
        final_letter = ""
        final_confidence = float(svc_confidence)

    return Response(
        {
            "letter": final_letter,
            "confidence": round(final_confidence, 2),
            "hand_detected": hand_detected,
            "svc_letter": svc_letter,
            "svc_confidence": round(float(svc_confidence), 2),
            "ai_letter": ai_letter,
            "ai_confidence": round(float(ai_confidence), 2),
            "ai_available": ai_available,
            "ai_error": ai_error,
        }
    )


def _redirect_for_role(role: str) -> str:
    if role == "instructor":
        return "instructor-dashboard.html"
    if role == "admin":
        return "admin-dashboard.html"
    return "dashboard.html"


def _get_year_label(year_level: str) -> str:
    normalized = str(year_level or "").strip()
    mapping = {
        "1": "1st Year",
        "2": "2nd Year",
        "3": "3rd Year",
        "4": "4th Year",
        "instructor": "Instructor",
        "admin": "Admin",
    }
    return mapping.get(normalized, normalized or "Student")


def _normalize_year_level_filter(value: str) -> str:
    normalized = str(value or "all").strip().lower()
    mapping = {
        "1": "1",
        "1st": "1",
        "1st year": "1",
        "first": "1",
        "2": "2",
        "2nd": "2",
        "2nd year": "2",
        "second": "2",
        "3": "3",
        "3rd": "3",
        "3rd year": "3",
        "third": "3",
        "4": "4",
        "4th": "4",
        "4th year": "4",
        "fourth": "4",
        "all": "all",
    }
    return mapping.get(normalized, normalized if normalized in {"1", "2", "3", "4"} else "all")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _leaderboard_entry_for_state(learning_state: UserLearningState) -> dict:
    user = learning_state.user
    profile = getattr(user, "profile", None)
    state = learning_state.state if isinstance(learning_state.state, dict) else {}
    module_progress = state.get("moduleProgress", {}) if isinstance(state.get("moduleProgress", {}), dict) else {}
    progress_values = [_safe_int(value) for value in module_progress.values()]
    year_level = str(getattr(profile, "year_level", "") or "").strip()
    name = getattr(profile, "full_name", "") or user.first_name or user.username.split("@")[0]

    return {
        "email": user.email,
        "name": name,
        "yearLevel": year_level,
        "yearLabel": _get_year_label(year_level),
        "role": getattr(profile, "role", "student") or "student",
        "points": _safe_int(state.get("points", 0)),
        "rank": _safe_int(state.get("rank", 0)),
        "streak": _safe_int(state.get("streak", 0)),
        "accuracy": _safe_int(state.get("accuracy", 0)),
        "completedActivities": _safe_int(state.get("completedActivities", 0)),
        "practiceMinutes": _safe_int(state.get("practiceMinutes", 0)),
        "modulesCompleted": sum(1 for value in progress_values if value >= 100),
        "averageProgress": round(sum(progress_values) / len(progress_values)) if progress_values else 0,
        "updatedAt": learning_state.updated_at.isoformat(),
    }


def _zero_learning_state_for_user(user: User) -> dict:
    profile = getattr(user, "profile", None)
    year_level = str(getattr(profile, "year_level", "") or "")
    learner_name = getattr(profile, "full_name", "") or user.first_name or user.username
    year_label = _get_year_label(year_level)

    return {
        "points": 0,
        "rank": 0,
        "accuracy": 0,
        "streak": 0,
        "completedActivities": 0,
        "practiceMinutes": 0,
        "weeklyActivity": [0, 0, 0, 0, 0, 0, 0],
        "moduleProgress": {
            "lesson1": 0,
            "lesson2": 0,
            "lesson3": 0,
            "lesson4": 0,
            "lesson5": 0,
            "lesson6": 0,
            "lesson7": 0,
            "lesson8": 0,
        },
        "recentActivity": [
            {"icon": "📚", "text": f"{learner_name} is ready to start learning", "meta": year_label},
        ],
        "achievements": [
            {"icon": "fas fa-graduation-cap", "name": "Quick Learner", "earned": False},
            {"icon": "fas fa-star", "name": "Perfect Score", "earned": False},
            {"icon": "fas fa-lock", "name": "Master Signer", "earned": False},
            {"icon": "fas fa-lock", "name": "FSL Expert", "earned": False},
            {"icon": "fas fa-lock", "name": "Champion", "earned": False},
        ],
        "leaderboard": [],
        "performance": [
            {"label": "Sign Recognition", "value": 0},
            {"label": "Finger-Spelling", "value": 0},
            {"label": "Sign Grammar", "value": 0},
            {"label": "Communication", "value": 0},
        ],
    }


def _is_seeded_learning_state(state: dict) -> bool:
    if not isinstance(state, dict):
        return False

    seeded_points = {1180, 2260, 3210, 4120}
    seeded_completed = {18, 31, 46, 60}
    seeded_streaks = {3, 5, 7, 9}
    seeded_accuracy = {79, 84, 88, 91}
    seeded_practice = {128, 214, 336, 460}

    points = _safe_int(state.get("points", 0))
    completed = _safe_int(state.get("completedActivities", 0))
    streak = _safe_int(state.get("streak", 0))
    accuracy = _safe_int(state.get("accuracy", 0))
    practice_minutes = _safe_int(state.get("practiceMinutes", 0))
    recent_activity = state.get("recentActivity", [])

    if points not in seeded_points:
        return False
    if completed not in seeded_completed:
        return False
    if streak not in seeded_streaks:
        return False
    if accuracy not in seeded_accuracy:
        return False
    if practice_minutes not in seeded_practice:
        return False
    if not isinstance(recent_activity, list) or not recent_activity:
        return False

    first_item = recent_activity[0] if isinstance(recent_activity[0], dict) else {}
    first_text = str(first_item.get("text", "")).lower()
    return "started structured modules" in first_text or "profile synced" in first_text


@api_view(["GET"])
def leaderboard(request: Any) -> Response:
    current_email = str(request.query_params.get("email") or "").strip().lower()
    sort_by = str(request.query_params.get("sortBy") or "points").strip().lower()
    year_level = _normalize_year_level_filter(request.query_params.get("yearLevel") or "all")
    try:
        limit = max(3, min(50, int(request.query_params.get("limit") or 10)))
    except Exception:
        limit = 10

    entries = [
        _leaderboard_entry_for_state(learning_state)
        for learning_state in UserLearningState.objects.select_related("user", "user__profile").all()
    ]

    # Student leaderboard only: exclude instructor/admin and any non-student year labels.
    entries = [
        entry
        for entry in entries
        if str(entry.get("role") or "").lower() == "student"
        and str(entry.get("yearLevel") or "") in {"1", "2", "3", "4"}
    ]

    entries = [entry for entry in entries if entry["points"] > 0]

    if year_level != "all":
        entries = [entry for entry in entries if entry["yearLevel"] == year_level]

    sort_key_map = {
        "streak": lambda entry: (entry["streak"], entry["points"], entry["accuracy"]),
        "accuracy": lambda entry: (entry["accuracy"], entry["points"], entry["streak"]),
        "recent": lambda entry: (entry["updatedAt"], entry["points"], entry["streak"]),
        "points": lambda entry: (entry["points"], entry["streak"], entry["accuracy"]),
    }
    sort_key = sort_key_map.get(sort_by, sort_key_map["points"])
    entries.sort(key=sort_key, reverse=True)

    for index, entry in enumerate(entries):
        entry["rank"] = index + 1
        entry["isCurrentUser"] = bool(current_email and entry["email"].lower() == current_email)

    current_user = next((entry for entry in entries if entry["isCurrentUser"]), None)
    current_index = entries.index(current_user) if current_user in entries else -1
    next_higher = entries[current_index - 1] if current_index > 0 else None
    next_lower = entries[current_index + 1] if current_index >= 0 and current_index + 1 < len(entries) else None

    summary = {
        "totalPlayers": len(entries),
        "averageAccuracy": round(sum(entry["accuracy"] for entry in entries) / len(entries)) if entries else 0,
        "longestStreak": max((entry["streak"] for entry in entries), default=0),
        "totalPoints": sum(entry["points"] for entry in entries),
    }

    return Response(
        {
            "players": entries[:limit],
            "totalPlayers": len(entries),
            "currentUser": current_user,
            "nextHigher": next_higher,
            "nextLower": next_lower,
            "summary": summary,
            "sortBy": sort_by,
            "yearLevel": year_level,
            "limit": limit,
        }
    )


@api_view(["GET"])
def public_announcements(request: Any) -> Response:
    try:
        limit = max(1, min(20, int(request.query_params.get("limit") or 5)))
    except Exception:
        limit = 5

    announcements = Announcement.objects.filter(is_published=True).order_by("-updated_at", "-created_at")[:limit]
    serializer = AnnouncementSerializer(announcements, many=True)
    return Response(serializer.data)


def _default_learning_state_for_user(user: User) -> dict:
    profile = getattr(user, "profile", None)
    year_level = str(getattr(profile, "year_level", "1") or "1")
    return _zero_learning_state_for_user(user)


def _signup_role_from_selection(role: str, security_pin: str) -> str | None:
    normalized_role = str(role or "student").strip().lower()
    normalized_pin = str(security_pin or "").strip()
    instructor_pin = os.getenv("KUMPAS_INSTRUCTOR_SIGNUP_PIN", "161018").strip()
    admin_pin = os.getenv("KUMPAS_ADMIN_SIGNUP_PIN", "161018").strip()

    if normalized_role == "student":
        return "student"

    if normalized_role == "instructor":
        return "instructor" if normalized_pin == instructor_pin else None

    if normalized_role == "admin":
        return "admin" if normalized_pin == admin_pin else None

    return None


def _get_learning_state_for_user(user: User) -> UserLearningState:
    learning_state, created = UserLearningState.objects.get_or_create(
        user=user,
        defaults={"state": _default_learning_state_for_user(user)},
    )
    if created or not learning_state.state or _is_seeded_learning_state(learning_state.state):
        learning_state.state = _default_learning_state_for_user(user)
        learning_state.save(update_fields=["state", "updated_at"])
    return learning_state


@api_view(["POST"])
def signup(request: Any) -> Response:
    serializer = SignupSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=400)

    data = serializer.validated_data
    email = data["email"].strip().lower()
    fullname = data["fullname"].strip()
    # Force student signup: role selection and PIN removed from public signup
    role = "student"
    year_level = str(data.get("yearLevel") or "").strip()
    password = data["password"]
    confirm_password = data["confirmPassword"]
    if password != confirm_password:
        return Response({"error": "Passwords do not match"}, status=400)

    if User.objects.filter(username=email).exists():
        return Response({"error": "Email is already registered"}, status=409)

    if not year_level:
        return Response({"error": "Year level is required for student accounts"}, status=400)

    # Simple sanitization: disallow angle brackets in name
    if "<" in fullname or ">" in fullname:
        return Response({"error": "Invalid characters in fullname"}, status=400)

    # Normalize year level to canonical 1-4 using helper
    year_level = _normalize_year_level_filter(year_level)

    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=fullname,
    )
    UserProfile.objects.create(
        user=user,
        full_name=fullname,
        year_level=year_level if role == "student" else "",
        role=role,
        security_pin="",
    )
    _get_learning_state_for_user(user)

    return Response(
        {
            "message": "Account created successfully",
            "user": {
                "name": fullname,
                "email": email,
                "yearLevel": year_level if role == "student" else "",
                "role": role,
            },
            "redirect": _redirect_for_role(role),
        },
        status=201,
    )


@api_view(["POST"])
def login(request: Any) -> Response:
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=400)

    data = serializer.validated_data
    email = data["email"].strip().lower()
    # Authenticate with email/password only. Role and PIN are no longer required from client.
    user = authenticate(username=email, password=data["password"])
    if not user:
        return Response({"error": "Invalid email or password"}, status=401)

    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            "full_name": user.first_name or email.split("@")[0],
            "role": "student",
            "year_level": "",
        },
    )
    _get_learning_state_for_user(user)

    return Response(
        {
            "message": "Login successful",
            "user": {
                "name": profile.full_name or user.first_name or email.split("@")[0],
                "email": user.email,
                "yearLevel": profile.year_level,
                "role": profile.role,
            },
            "redirect": _redirect_for_role(profile.role),
        }
    )


@api_view(["GET", "POST"])
def learning_state(request: Any) -> Response:
    email = str(request.query_params.get("email") or request.data.get("email") or "").strip().lower()
    if not email:
        return Response({"error": "Missing email"}, status=400)

    try:
        user = User.objects.get(username=email)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    user_learning_state = _get_learning_state_for_user(user)

    if request.method == "GET":
        serializer = LearningStateSerializer(user_learning_state)
        return Response(serializer.data)

    state = request.data.get("state")
    if not isinstance(state, dict):
        return Response({"error": "state must be an object"}, status=400)

    user_learning_state.state = state
    user_learning_state.save(update_fields=["state", "updated_at"])
    serializer = LearningStateSerializer(user_learning_state)
    return Response(serializer.data)


def _request_email(request: Any) -> str:
    return str(request.query_params.get("email") or request.data.get("email") or "").strip().lower()


def _default_student_modules() -> list[dict[str, Any]]:
    return [
        {
            "module_key": "lesson1",
            "title": "Lesson 1: Basic Finger Spelling",
            "year_level": "1",
            "description": "Start with alphabet hand shapes and spelling drills.",
            "activities_count": 4,
            "status": LearningModule.STATUS_PUBLISHED,
            "sort_order": 1,
        },
        {
            "module_key": "lesson2",
            "title": "Lesson 2: Common Everyday Signs",
            "year_level": "1",
            "description": "Build essential sign vocabulary for daily communication.",
            "activities_count": 5,
            "status": LearningModule.STATUS_PUBLISHED,
            "sort_order": 2,
        },
        {
            "module_key": "lesson3",
            "title": "Lesson 3: Greetings and Polite Expressions",
            "year_level": "2",
            "description": "Practice polite conversational signs.",
            "activities_count": 4,
            "status": LearningModule.STATUS_PUBLISHED,
            "sort_order": 3,
        },
        {
            "module_key": "lesson4",
            "title": "Lesson 4: Family and Relationships",
            "year_level": "2",
            "description": "Describe people and relationships around you.",
            "activities_count": 5,
            "status": LearningModule.STATUS_PUBLISHED,
            "sort_order": 4,
        },
        {
            "module_key": "lesson5",
            "title": "Lesson 5: Numbers and Counting",
            "year_level": "3",
            "description": "Use numerical signs accurately in context.",
            "activities_count": 6,
            "status": LearningModule.STATUS_PUBLISHED,
            "sort_order": 5,
        },
        {
            "module_key": "lesson6",
            "title": "Lesson 6: Sign Language Grammar",
            "year_level": "3",
            "description": "Build clear sentence structure and grammar.",
            "activities_count": 6,
            "status": LearningModule.STATUS_PUBLISHED,
            "sort_order": 6,
        },
        {
            "module_key": "lesson7",
            "title": "Lesson 7: Emotions and Expressions",
            "year_level": "4",
            "description": "Express emotions naturally through signs.",
            "activities_count": 7,
            "status": LearningModule.STATUS_PUBLISHED,
            "sort_order": 7,
        },
        {
            "module_key": "lesson8",
            "title": "Lesson 8: Complex Conversations",
            "year_level": "4",
            "description": "Handle practical real-life sign conversations.",
            "activities_count": 8,
            "status": LearningModule.STATUS_PUBLISHED,
            "sort_order": 8,
        },
    ]


def _game_access_for_year(year_level: str) -> list[dict[str, Any]]:
    year_to_game = {
        "1": ("sign-match-game.html", "Sign Match Game"),
        "2": ("typing-game.html", "Sign-to-Word Typing"),
        "3": ("sentence-game.html", "Sentence Builder"),
        "4": ("scenario-game.html", "Scenario-Based Game"),
    }
    game_route, game_title = year_to_game.get(str(year_level), ("sign-match-game.html", "Sign Match Game"))

    def _difficulty_payload(level_name: str) -> dict[str, Any]:
        levels = [1, 2, 3]
        return {
            "difficulty": level_name,
            "levels": levels,
            "randomLevel": random.choice(levels),
        }

    return [
        {
            "yearLevel": str(year_level),
            "title": game_title,
            "route": game_route,
            "difficulties": [
                _difficulty_payload("easy"),
                _difficulty_payload("medium"),
                _difficulty_payload("hard"),
            ],
        }
    ]


@api_view(["GET"])
def student_content(request: Any) -> Response:
    email = _request_email(request)
    if not email:
        return Response({"error": "Missing email"}, status=400)

    try:
        user = User.objects.select_related("profile").get(username=email)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    profile = getattr(user, "profile", None)
    if not profile or str(profile.role or "student").lower() != "student":
        return Response({"error": "Student access required"}, status=403)

    year_level = _normalize_year_level_filter(getattr(profile, "year_level", "1") or "1")
    if year_level not in {"1", "2", "3", "4"}:
        year_level = "1"

    modules = list(
        LearningModule.objects.filter(year_level=year_level, status=LearningModule.STATUS_PUBLISHED)
        .order_by("sort_order", "title")
        .all()
    )

    if modules:
        modules_payload = LearningModuleSerializer(modules, many=True).data
    else:
        modules_payload = [
            module
            for module in _default_student_modules()
            if str(module.get("year_level") or "") == year_level
        ]

    return Response(
        {
            "yearLevel": year_level,
            "modules": modules_payload,
            "gameAccess": _game_access_for_year(year_level),
        }
    )


def _get_instructor_actor(request: Any):
    email = _request_email(request)
    if not email:
        return None, Response({"error": "Missing instructor email"}, status=400)

    try:
        user = User.objects.select_related("profile").get(username=email)
    except User.DoesNotExist:
        return None, Response({"error": "User not found"}, status=404)

    profile = getattr(user, "profile", None)
    if not profile or profile.role not in {"instructor", "admin"}:
        return None, Response({"error": "Instructor access required"}, status=403)

    return user, None


def _module_key_for_title(title: str) -> str:
    base_key = slugify(str(title or "module").strip()) or "module"
    candidate = base_key
    suffix = 2
    while LearningModule.objects.filter(module_key=candidate).exists():
        candidate = f"{base_key}-{suffix}"
        suffix += 1
    return candidate


def _module_student_counts(modules: list[LearningModule]) -> dict[str, int]:
    counts = {module.module_key: 0 for module in modules}
    learning_states = UserLearningState.objects.select_related("user", "user__profile").all()

    for learning_state in learning_states:
        profile = getattr(learning_state.user, "profile", None)
        if not profile or profile.role != "student":
            continue

        state = learning_state.state if isinstance(learning_state.state, dict) else {}
        progress_map = state.get("moduleProgress", {}) if isinstance(state.get("moduleProgress", {}), dict) else {}
        for module in modules:
            if _safe_int(progress_map.get(module.module_key, 0)) >= 100:
                counts[module.module_key] = counts.get(module.module_key, 0) + 1

    return counts


def _serialize_student_row(learning_state: UserLearningState, total_modules: int) -> dict:
    user = learning_state.user
    profile = getattr(user, "profile", None)
    state = learning_state.state if isinstance(learning_state.state, dict) else {}
    progress_map = state.get("moduleProgress", {}) if isinstance(state.get("moduleProgress", {}), dict) else {}
    completed_modules = sum(1 for value in progress_map.values() if _safe_int(value) >= 100)
    average_progress = round(sum(_safe_int(value) for value in progress_map.values()) / len(progress_map)) if progress_map else 0
    name = getattr(profile, "full_name", "") or user.first_name or user.username.split("@")[0]

    return {
        "email": user.email,
        "name": name,
        "yearLevel": str(getattr(profile, "year_level", "") or ""),
        "yearLabel": _get_year_label(getattr(profile, "year_level", "") or ""),
        "points": _safe_int(state.get("points", 0)),
        "streak": _safe_int(state.get("streak", 0)),
        "accuracy": _safe_int(state.get("accuracy", 0)),
        "modulesCompleted": completed_modules,
        "totalModules": total_modules,
        "overallProgress": average_progress,
        "updatedAt": learning_state.updated_at.isoformat(),
    }


def _student_learning_state(user: User) -> UserLearningState | None:
    return UserLearningState.objects.filter(user=user).first()


def _instructor_fallback_payload(actor: User) -> dict:
    profile = getattr(actor, "profile", None)
    return {
        "currentUser": {
            "email": actor.email,
            "name": getattr(profile, "full_name", "") or actor.first_name or actor.username,
            "role": getattr(profile, "role", "instructor") or "instructor",
        },
        "summary": {
            "totalStudents": 0,
            "activeStudents": 0,
            "totalModules": 0,
            "publishedModules": 0,
            "totalAnnouncements": 0,
            "averageCompletion": 0,
            "averageAccuracy": 0,
            "totalPoints": 0,
        },
        "modules": [],
        "students": [],
        "announcements": [],
        "warning": "Instructor database tables are not ready yet. Run migrations first.",
    }


@api_view(["GET"])
def instructor_dashboard(request: Any) -> Response:
    actor, error_response = _get_instructor_actor(request)
    if error_response:
        return error_response

    try:
        modules = list(LearningModule.objects.select_related("created_by", "updated_by").all())
        announcements = list(Announcement.objects.select_related("created_by", "updated_by").all())
        student_profiles = list(
            UserProfile.objects.select_related("user")
            .filter(role="student")
            .order_by("full_name", "user__username")
        )
        student_states = {state.user_id: state for state in UserLearningState.objects.select_related("user", "user__profile").all()}
        module_counts = _module_student_counts(modules)
        total_modules = len(modules)
    except (DatabaseError, OperationalError):
        return Response(_instructor_fallback_payload(actor))

    students = []
    total_points = 0
    total_completion = 0
    active_students = 0
    for profile in student_profiles:
        learning_state = student_states.get(profile.user_id)
        if not learning_state:
            learning_state = _get_learning_state_for_user(profile.user)
            student_states[profile.user_id] = learning_state
        student_row = _serialize_student_row(learning_state, total_modules)
        total_points += student_row["points"]
        total_completion += student_row["overallProgress"]
        if student_row["points"] > 0 or student_row["modulesCompleted"] > 0:
            active_students += 1
        students.append(student_row)

    students.sort(key=lambda item: (item["points"], item["overallProgress"], item["accuracy"]), reverse=True)

    # Pagination for student list
    page = _safe_int(request.query_params.get("page"), 1)
    page_size = _safe_int(request.query_params.get("pageSize"), 25)
    total_students = len(students)
    start = max(0, (page - 1) * page_size)
    end = start + page_size
    students_page = students[start:end]

    summary = {
        "totalStudents": len(student_profiles),
        "activeStudents": active_students,
        "totalModules": total_modules,
        "publishedModules": sum(1 for module in modules if module.status == LearningModule.STATUS_PUBLISHED),
        "totalAnnouncements": len(announcements),
        "averageCompletion": round(total_completion / len(students)) if students else 0,
        "averageAccuracy": round(sum(student["accuracy"] for student in students) / len(students)) if students else 0,
        "totalPoints": total_points,
    }

    payload = {
        "currentUser": {
            "email": actor.email,
            "name": getattr(getattr(actor, "profile", None), "full_name", "") or actor.first_name or actor.username,
            "role": getattr(getattr(actor, "profile", None), "role", "instructor") or "instructor",
        },
        "summary": summary,
        "modules": [
            {
                **LearningModuleSerializer(module).data,
                "studentCount": module_counts.get(module.module_key, 0),
            }
            for module in modules
        ],
        "students": students_page,
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "total": total_students,
        },
        "announcements": AnnouncementSerializer(announcements, many=True).data,
    }
    return Response(payload)


@api_view(["GET", "POST"])
def instructor_modules(request: Any) -> Response:
    actor, error_response = _get_instructor_actor(request)
    if error_response:
        return error_response

    if request.method == "GET":
        try:
            modules = LearningModule.objects.select_related("created_by", "updated_by").all()
            module_counts = _module_student_counts(list(modules))
            return Response([
                {
                    **LearningModuleSerializer(module).data,
                    "studentCount": module_counts.get(module.module_key, 0),
                }
                for module in modules
            ])
        except (DatabaseError, OperationalError):
            return Response([])

    payload = request.data.copy()
    title = str(payload.get("title") or "").strip()
    if not title:
        return Response({"error": "Module title is required"}, status=400)

    module_key = str(payload.get("module_key") or payload.get("moduleKey") or "").strip()
    if not module_key:
        module_key = _module_key_for_title(title)
    elif LearningModule.objects.filter(module_key=module_key).exists():
        return Response({"error": "Module key already exists"}, status=409)

    serializer = LearningModuleSerializer(data={
        "module_key": module_key,
        "title": title,
        "year_level": str(payload.get("year_level") or payload.get("yearLevel") or "1").strip(),
        "description": str(payload.get("description") or "").strip(),
        "activities_count": _safe_int(payload.get("activities_count") or payload.get("activitiesCount") or 0),
        "status": str(payload.get("status") or LearningModule.STATUS_DRAFT).strip(),
        "sort_order": _safe_int(payload.get("sort_order") or payload.get("sortOrder") or 0),
    })
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=400)

    module = serializer.save(created_by=actor, updated_by=actor)
    response_data = LearningModuleSerializer(module).data
    response_data["studentCount"] = 0
    return Response(response_data, status=201)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
def instructor_module_detail(request: Any, module_id: int) -> Response:
    actor, error_response = _get_instructor_actor(request)
    if error_response:
        return error_response

    module = get_object_or_404(LearningModule, pk=module_id)

    if request.method == "GET":
        data = LearningModuleSerializer(module).data
        data["studentCount"] = _module_student_counts([module]).get(module.module_key, 0)
        return Response(data)

    if request.method == "DELETE":
        module.delete()
        return Response({"message": "Module deleted"})

    payload = request.data.copy()
    update_data = {
        "module_key": str(payload.get("module_key") or module.module_key).strip() or module.module_key,
        "title": str(payload.get("title") or module.title).strip(),
        "year_level": str(payload.get("year_level") or payload.get("yearLevel") or module.year_level).strip(),
        "description": str(payload.get("description") or module.description).strip(),
        "activities_count": _safe_int(payload.get("activities_count") or payload.get("activitiesCount") or module.activities_count),
        "status": str(payload.get("status") or module.status).strip(),
        "sort_order": _safe_int(payload.get("sort_order") or payload.get("sortOrder") or module.sort_order),
    }
    if update_data["module_key"] != module.module_key and LearningModule.objects.exclude(pk=module.pk).filter(module_key=update_data["module_key"]).exists():
        return Response({"error": "Module key already exists"}, status=409)

    serializer = LearningModuleSerializer(module, data=update_data, partial=True)
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=400)

    module = serializer.save(updated_by=actor)
    data = LearningModuleSerializer(module).data
    data["studentCount"] = _module_student_counts([module]).get(module.module_key, 0)
    return Response(data)


@api_view(["GET", "POST"])
def instructor_announcements(request: Any) -> Response:
    actor, error_response = _get_instructor_actor(request)
    if error_response:
        return error_response

    if request.method == "GET":
        try:
            announcements = Announcement.objects.select_related("created_by", "updated_by").all()
            return Response(AnnouncementSerializer(announcements, many=True).data)
        except (DatabaseError, OperationalError):
            return Response([])

    serializer = AnnouncementSerializer(data={
        "title": str(request.data.get("title") or "").strip(),
        "message": str(request.data.get("message") or "").strip(),
        "is_published": _safe_bool(request.data.get("is_published", True), True),
    })
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=400)

    announcement = serializer.save(created_by=actor, updated_by=actor)
    return Response(AnnouncementSerializer(announcement).data, status=201)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
def instructor_announcement_detail(request: Any, announcement_id: int) -> Response:
    actor, error_response = _get_instructor_actor(request)
    if error_response:
        return error_response

    announcement = get_object_or_404(Announcement, pk=announcement_id)

    if request.method == "GET":
        return Response(AnnouncementSerializer(announcement).data)

    if request.method == "DELETE":
        announcement.delete()
        return Response({"message": "Announcement deleted"})

    serializer = AnnouncementSerializer(
        announcement,
        data={
            "title": str(request.data.get("title") or announcement.title).strip(),
            "message": str(request.data.get("message") or announcement.message).strip(),
            "is_published": _safe_bool(request.data.get("is_published", announcement.is_published), announcement.is_published),
        },
        partial=True,
    )
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=400)

    announcement = serializer.save(updated_by=actor)
    return Response(AnnouncementSerializer(announcement).data)


@api_view(["GET", "POST"])
def module_files(request: Any, module_id: int) -> Response:
    """Get files for a module or upload a new file"""
    actor, error_response = _get_instructor_actor(request)
    if error_response:
        return error_response

    module = get_object_or_404(LearningModule, pk=module_id)

    if request.method == "GET":
        try:
            files = ModuleFile.objects.filter(module=module).all()
            return Response(ModuleFileSerializer(files, many=True, context={"request": request}).data)
        except (DatabaseError, OperationalError):
            return Response([])

    # POST - Upload new file
    if "file" not in request.FILES:
        return Response({"error": "No file provided"}, status=400)

    uploaded_file = request.FILES["file"]
    file_name = str(uploaded_file.name or "").strip()
    if not file_name:
        return Response({"error": "Invalid file name"}, status=400)

    # Determine file type
    file_ext = str(file_name.split(".")[-1] if "." in file_name else "").lower()
    file_type = _get_file_type(file_ext)

    try:
        module_file = ModuleFile.objects.create(
            module=module,
            file=uploaded_file,
            file_name=file_name,
            file_type=file_type,
            file_size=uploaded_file.size,
            description=str(request.data.get("description", "")).strip(),
            uploaded_by=actor,
        )
        return Response(ModuleFileSerializer(module_file, context={"request": request}).data, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(["DELETE"])
def module_file_detail(request: Any, module_id: int, file_id: int) -> Response:
    """Delete a file from a module"""
    actor, error_response = _get_instructor_actor(request)
    if error_response:
        return error_response

    module = get_object_or_404(LearningModule, pk=module_id)
    module_file = get_object_or_404(ModuleFile, pk=file_id, module=module)

    # Delete the actual file
    if module_file.file:
        module_file.file.delete()

    module_file.delete()
    return Response({"message": "File deleted"})


def _get_file_type(file_ext: str) -> str:
    """Determine file type from extension"""
    doc_exts = {"pdf", "doc", "docx", "txt", "xls", "xlsx"}
    pres_exts = {"ppt", "pptx"}
    video_exts = {"mp4", "avi", "mov", "mkv", "flv"}
    image_exts = {"jpg", "jpeg", "png", "gif", "bmp"}
    audio_exts = {"mp3", "wav", "flac", "aac", "m4a"}

    if file_ext in doc_exts:
        return "document"
    elif file_ext in pres_exts:
        return "presentation"
    elif file_ext in video_exts:
        return "video"
    elif file_ext in image_exts:
        return "image"
    elif file_ext in audio_exts:
        return "audio"
    else:
        return "other"
