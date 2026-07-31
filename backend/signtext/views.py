import base64
import os
import random
from datetime import timedelta
from django.utils import timezone
from typing import Any
from django.db import DatabaseError, OperationalError
from django.db.models import F, Q, Sum
from django.contrib.auth import authenticate, login as django_login
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

from .ai_word_inference import get_last_ai_error, predict_with_openrouter
from .fingerspelling_svc import predict_letter_from_landmarks
from .inference import predict_from_image_bytes
from .word_sequence_svc import MODEL_PATH as WORD_MODEL_PATH, predict_word_from_sequence
from .models import (
    Achievement,
    Announcement,
    GameLevel,
    GameLevelItem,
    LearningModule,
    ModuleFile,
    QuizAttempt,
    QuizQuestion,
    SignPredictionLog,
    SignVideo,
    UserAchievement,
    UserLearningState,
    UserProfile,
    EmailOTP,
)
from .serializers import (
    AdminSignVideoSerializer,
    AnnouncementSerializer,
    GameLevelItemSerializer,
    GameLevelSerializer,
    LearningModuleSerializer,
    LearningStateSerializer,
    LoginSerializer,
    ModuleFileSerializer,
    QuizQuestionSerializer,
    StudentQuizQuestionSerializer,
    SignPredictionLogSerializer,
    SignVideoSerializer,
    SignupSerializer,
)


AVATAR_PRESET_IDS = {
    "blue", "purple", "pink", "green", "orange", "teal", "yellow", "red",
    "indigo", "lime", "cyan", "rose",
}


def _profile_avatar_payload(profile: "UserProfile", request: Any) -> dict:
    photo_url = ""
    if profile and profile.photo and hasattr(profile.photo, "url"):
        photo_url = request.build_absolute_uri(profile.photo.url)
    return {
        "photoUrl": photo_url,
        "avatarId": (profile.avatar_id if profile else "") or "",
    }


@csrf_exempt
@api_view(["POST", "PATCH"])
def profile_photo(request: Any) -> Response:
    """Upload/update a user's profile photo, or set a preset avatar id.

    Accepts either multipart/form-data with a 'photo' file, or an 'avatar_id'
    field naming one of AVATAR_PRESET_IDS. The two are mutually exclusive:
    setting one clears the other.
    """
    email = str(request.data.get("email") or request.query_params.get("email") or "").strip().lower()
    if not email:
        return Response({"error": "Missing email"}, status=400)

    try:
        user = User.objects.get(username=email)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    profile = getattr(user, "profile", None)
    if not profile:
        profile = UserProfile.objects.create(user=user, full_name=user.first_name or user.username)

    photo_file = request.FILES.get("photo")
    avatar_id = str(request.data.get("avatar_id") or "").strip().lower()

    if photo_file:
        profile.photo = photo_file
        profile.avatar_id = ""
        profile.save(update_fields=["photo", "avatar_id"])
    elif avatar_id:
        if avatar_id not in AVATAR_PRESET_IDS:
            return Response({"error": "Invalid avatar_id"}, status=400)
        profile.photo.delete(save=False)
        profile.avatar_id = avatar_id
        profile.save(update_fields=["photo", "avatar_id"])
    elif "avatar_id" in request.data and not avatar_id:
        # Explicit empty avatar_id clears both photo and preset avatar.
        profile.photo.delete(save=False)
        profile.avatar_id = ""
        profile.save(update_fields=["photo", "avatar_id"])
    else:
        return Response({"error": "Missing photo file (field 'photo') or 'avatar_id'"}, status=400)

    payload = _profile_avatar_payload(profile, request)
    return Response({"message": "Photo updated", **payload})


@csrf_exempt
@api_view(["POST", "PATCH"])
def profile_update(request: Any) -> Response:
    """Update editable UserProfile fields (student ID, contact number, hearing
    status) for the signed-in student. Mirrors profile_photo's email-based
    lookup so it works the same way as the rest of the profile endpoints.
    """
    email = str(request.data.get("email") or request.query_params.get("email") or "").strip().lower()
    if not email:
        return Response({"error": "Missing email"}, status=400)

    try:
        user = User.objects.get(username=email)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    profile = getattr(user, "profile", None)
    if not profile:
        profile = UserProfile.objects.create(user=user, full_name=user.first_name or user.username)

    editable_fields = ["student_id", "contact_number", "hearing_status"]
    update_fields = []
    for field in editable_fields:
        if field in request.data:
            setattr(profile, field, str(request.data.get(field) or "").strip())
            update_fields.append(field)

    if update_fields:
        profile.save(update_fields=update_fields)

    return Response({
        "message": "Profile updated",
        "studentId": profile.student_id,
        "contactNumber": profile.contact_number,
        "hearingStatus": profile.hearing_status,
    })


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


@api_view(["POST"])
def predict_word_sequence(request: Any) -> Response:
    """Classify a short (~1-3s) two-hand landmark sequence as a locally-trained word/phrase.

    Each frame is {"left": [[x,y,z]]*21|null, "right": [...]|null}. Returns
    empty/zero-confidence until a real model has been trained from recorded
    data (see backend/scripts/train_word_model.py) -- there is no synthetic
    fallback for gestures the way there is for static letters.

    Optionally accepts an "image" (single current-frame JPEG data URL) and
    "use_ai" flag, mirroring predict_fingerspelling's hybrid pattern: the
    cloud AI fallback is only consulted when local confidence is low and an
    OpenRouter API key is configured, to keep the common case fast.
    """
    frames = request.data.get("frames", [])
    image_data = request.data.get("image", "")
    use_ai = bool(request.data.get("use_ai", False))

    if not isinstance(frames, list):
        return Response({"error": "frames must be a list"}, status=400)

    word, confidence = predict_word_from_sequence(frames)

    ai_word = ""
    ai_confidence = 0.0
    ai_available = False
    ai_error = ""

    ai_key_present = bool(os.getenv("OPENROUTER_API_KEY", "").strip())
    low_local_confidence = (not word) or float(confidence) < 40.0
    if use_ai and ai_key_present and low_local_confidence and isinstance(image_data, str) and image_data.strip():
        ai_prediction = predict_with_openrouter(image_data)
        ai_available = ai_prediction is not None
        if ai_prediction is not None:
            ai_pred_label, ai_pred_conf, _ai_hand_detected = ai_prediction
            ai_pred_label = str(ai_pred_label or "").strip().upper()
            if ai_pred_label and ai_pred_label not in {"NO HAND DETECTED", "NONE"} and ai_pred_conf >= 35:
                ai_word = ai_pred_label
                ai_confidence = float(ai_pred_conf)
        else:
            ai_error = get_last_ai_error()

    final_word = word
    final_confidence = float(confidence)
    if not word and ai_word:
        final_word = ai_word
        final_confidence = ai_confidence
    elif word and ai_word and word != ai_word and ai_confidence > float(confidence):
        final_word = ai_word
        final_confidence = ai_confidence

    return Response(
        {
            "word": final_word,
            "confidence": round(final_confidence, 2),
            "model_available": WORD_MODEL_PATH.exists(),
            "svc_word": word,
            "svc_confidence": round(float(confidence), 2),
            "ai_word": ai_word,
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


def _skill_breakdown_for_user(user: User) -> list:
    """Per-module quiz accuracy, derived from real QuizAttempt rows.

    Sums score/total across all attempts per module (so retakes average
    together), returned as [{label, value}] sorted strongest-first to match
    how the dashboard/profile UI slices this list (first N = strengths,
    last N = focus areas).
    """
    rows = (
        QuizAttempt.objects.filter(user=user)
        .values("module_id", "module__title")
        .annotate(total_score=Sum("score"), total_total=Sum("total"))
    )
    breakdown = []
    for row in rows:
        total = row["total_total"] or 0
        if total <= 0:
            continue
        pct = round((row["total_score"] or 0) / total * 100)
        breakdown.append({"label": row["module__title"], "value": pct})
    breakdown.sort(key=lambda item: item["value"], reverse=True)
    return breakdown


def _evaluate_achievements(user: User, state: dict) -> list:
    """Unlocks any newly-qualified achievements for this user and returns
    the full catalog as [{earned, icon, name}], matching the shape the
    dashboard/profile rendering already expects.
    """
    module_progress = state.get("moduleProgress", {}) if isinstance(state.get("moduleProgress"), dict) else {}
    modules_completed = sum(1 for value in module_progress.values() if _safe_int(value) >= 100)
    points_total = _safe_int(state.get("points"))
    streak_days = _safe_int(state.get("streak"))

    quiz_attempts = QuizAttempt.objects.filter(user=user)
    quiz_count = quiz_attempts.count()
    has_perfect_quiz = quiz_attempts.filter(total__gt=0, score=F("total")).exists()

    metric_by_criteria = {
        Achievement.CRITERIA_MODULES_COMPLETED: modules_completed,
        Achievement.CRITERIA_STREAK_DAYS: streak_days,
        Achievement.CRITERIA_QUIZ_PERFECT_SCORE: 1 if has_perfect_quiz else 0,
        Achievement.CRITERIA_QUIZ_COUNT: quiz_count,
        Achievement.CRITERIA_POINTS_TOTAL: points_total,
    }

    achievements = list(Achievement.objects.filter(is_active=True))
    unlocked_keys = set(
        UserAchievement.objects.filter(user=user, achievement__in=achievements)
        .values_list("achievement__key", flat=True)
    )

    newly_unlocked = [
        achievement
        for achievement in achievements
        if achievement.key not in unlocked_keys
        and metric_by_criteria.get(achievement.criteria_type, 0) >= achievement.criteria_value
    ]
    if newly_unlocked:
        UserAchievement.objects.bulk_create(
            [UserAchievement(user=user, achievement=achievement) for achievement in newly_unlocked],
            ignore_conflicts=True,
        )
        unlocked_keys.update(achievement.key for achievement in newly_unlocked)

    return [
        {"earned": achievement.key in unlocked_keys, "icon": achievement.icon, "name": achievement.name}
        for achievement in achievements
    ]


def _leaderboard_entry_for_state(learning_state: UserLearningState, request: Any = None) -> dict:
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
        **(_profile_avatar_payload(profile, request) if request is not None else {"photoUrl": "", "avatarId": ""}),
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
        "recentActivity": [],
        "achievements": [],
        "leaderboard": [],
        "performance": [],
    }


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
        _leaderboard_entry_for_state(learning_state, request)
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


def _generate_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


def _find_user_by_identifier(identifier: str) -> User | None:
    normalized = str(identifier or "").strip().lower()
    if not normalized:
        return None
    return User.objects.filter(
        Q(username__iexact=normalized) | Q(email__iexact=normalized)
    ).first()


def _create_and_send_otp(user: User, request: Any, minutes_valid: int = 15, purpose: str = "verification") -> dict:
    otp = _generate_otp()
    expires = timezone.now() + timedelta(minutes=minutes_valid)
    
    # Validate that user has an email
    if not user.email or not user.email.strip():
        error_msg = f"User {user.username} has no email address set"
        logger.error(error_msg)
        return {"ok": False, "error": error_msg}
    
    recipient_email = user.email.strip()
    
    # Keep only one active OTP window for the user so retries do not stack multiple usable codes.
    EmailOTP.objects.filter(user=user, expires_at__gte=timezone.now()).delete()
    EmailOTP.objects.create(user=user, otp=otp, expires_at=expires)
    
    if purpose == "password_reset":
        subject = "Your Kumpas password reset code"
        message = f"Your password reset code is: {otp}\nIt will expire in {minutes_valid} minutes."
    else:
        subject = "Your Kumpas verification code"
        message = f"Your verification code is: {otp}\nIt will expire in {minutes_valid} minutes."
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
    
    try:
        logger.info(f"Attempting to send {purpose} OTP {otp} to {recipient_email}")
        send_mail(subject, message, from_email, [recipient_email], fail_silently=False)
        logger.info(f"OTP successfully sent to {recipient_email}")
        return {"ok": True, "error": None}
    except Exception as e:
        error_msg = f"Failed to send {purpose} email to {recipient_email}: {str(e)}"
        logger.exception(error_msg)
        return {"ok": False, "error": error_msg}


def _normalize_name_part(name: str) -> str:
    normalized = str(name or "").strip()
    if not normalized:
        return ""
    normalized = " ".join(normalized.split())
    return " ".join(
        part.capitalize() if part else ""
        for part in normalized.split(" ")
    ).strip()


def _get_learning_state_for_user(user: User) -> UserLearningState:
    learning_state, created = UserLearningState.objects.get_or_create(
        user=user,
        defaults={"state": _default_learning_state_for_user(user)},
    )
    if created or not learning_state.state:
        learning_state.state = _default_learning_state_for_user(user)
        learning_state.save(update_fields=["state", "updated_at"])
    return learning_state


@csrf_exempt
@api_view(["POST"])
def signup(request: Any) -> Response:
    serializer = SignupSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=400)

    data = serializer.validated_data
    email = data["email"].strip().lower()
    first_name = _normalize_name_part(data["firstName"])
    middle_name = _normalize_name_part(data.get("middleName") or "")
    last_name = _normalize_name_part(data["lastName"])
    suffix = _normalize_name_part(data.get("suffix") or "")
    year_level = str(data.get("yearLevel") or "").strip()
    password = data["password"]
    confirm_password = data["confirmPassword"]
    # Public signup only creates student accounts
    role = "student"

    if password != confirm_password:
        return Response({"error": "Passwords do not match"}, status=400)

    existing_user = User.objects.select_related("profile").filter(username=email).first()
    if existing_user:
        existing_profile = getattr(existing_user, "profile", None)
        existing_role = str(getattr(existing_profile, "role", "student") or "student").lower()

        # If the account already exists but is still inactive, treat this as a pending verification case.
        if not existing_user.is_active and existing_role == "student":
            result = _create_and_send_otp(existing_user, request)
            response = {
                "message": "Account already exists but is still pending verification. A new verification code was sent.",
                "user": {
                    "id": existing_user.id,
                    "name": getattr(existing_profile, "full_name", "") or existing_user.first_name or email.split("@")[0],
                    "email": email,
                    "username": existing_user.username,
                    "yearLevel": getattr(existing_profile, "year_level", year_level) or year_level,
                    "role": "student",
                },
                "redirect": f"verify-email.html?email={email}",
            }
            if not result.get("ok"):
                response["message"] = "Account already exists but verification email could not be sent right now. You can try resending it on the verification page."
                response["warning"] = "email_delivery_failed"
                response["details"] = "Check server logs for SMTP error."
            return Response(response, status=201)

        return Response({"error": "Email is already registered"}, status=409)

    if not year_level:
        return Response({"error": "Year level is required for student accounts"}, status=400)

    if not first_name or not last_name:
        return Response({"error": "First name and last name are required"}, status=400)

    full_name = " ".join([part for part in [first_name, middle_name, last_name, suffix] if part])

    # Create the user account immediately; no email verification gate.
    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )

    if role == "student":
        # Create profile and require email verification before activation.
        UserProfile.objects.create(
            user=user,
            full_name=full_name,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            suffix=suffix,
            year_level=year_level,
            role=role,
            security_pin="",
        )

        # Mark user inactive until they verify their email
        user.is_active = False
        user.save(update_fields=["is_active"])

        # Create and send OTP; if sending fails include error details but still instruct user to verify
        otp_result = _create_and_send_otp(user, request)
        response = {
            "message": "Account created. A verification code was sent to your email.",
            "user": {
                "id": user.id,
                "name": full_name,
                "email": email,
                "username": user.username,
                "yearLevel": year_level,
                "role": role,
            },
            "redirect": f"verify-email.html?email={email}",
        }
        if not otp_result.get("ok"):
            response["warning"] = "email_delivery_failed"
            response["details"] = otp_result.get("error")

        return Response(response, status=201)

    # Non-student accounts are activated immediately
    UserProfile.objects.create(
        user=user,
        full_name=full_name,
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        suffix=suffix,
        year_level=year_level,
        role=role,
        security_pin="",
    )
    _get_learning_state_for_user(user)

    return Response({
        "message": "Account created successfully",
        "user": {
            "id": user.id,
            "name": full_name,
            "email": email,
            "yearLevel": year_level if role == "student" else "",
            "role": role,
        },
        "redirect": _redirect_for_role(role),
    }, status=201)


@csrf_exempt
@api_view(["POST"])
def login(request: Any) -> Response:
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=400)

    data = serializer.validated_data
    identifier = str(data["email"] or "").strip()
    if not identifier:
        return Response({"error": "Email or username is required"}, status=400)

    # Accept both username and email as login identifier.
    # Build candidate list then pick the account with matching password.
    candidates: list[User] = []
    seen_ids: set[int] = set()

    def add_candidate(qs):
        for cand in qs[:25]:
            if cand.id not in seen_ids:
                seen_ids.add(cand.id)
                candidates.append(cand)

    add_candidate(User.objects.filter(username__iexact=identifier))
    add_candidate(User.objects.filter(email__iexact=identifier))

    if "@" not in identifier:
        add_candidate(User.objects.filter(username__istartswith=f"{identifier}@"))
        add_candidate(User.objects.filter(email__istartswith=f"{identifier}@"))
    else:
        local_part = identifier.split("@", 1)[0]
        add_candidate(User.objects.filter(username__iexact=local_part))
        add_candidate(User.objects.filter(email__istartswith=f"{local_part}@"))
        add_candidate(User.objects.filter(username__istartswith=f"{local_part}@"))

    user = next((cand for cand in candidates if cand.check_password(data["password"])), None)
    if not user:
        return Response({"error": "Invalid username/email or password"}, status=401)

    auth_username = user.username

    if not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])

    user = authenticate(username=auth_username, password=data["password"])
    if not user:
        return Response({"error": "Invalid username/email or password"}, status=401)

    django_login(request, user)

    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            "full_name": user.first_name or user.username.split("@")[0],
            "role": "student",
            "year_level": "",
        },
    )
    _get_learning_state_for_user(user)

    # Don't require client-sent role or PIN. Server determines role from profile.

    return Response(
        {
            "message": "Login successful",
            "user": {
                "id": user.id,
                "name": profile.full_name or user.first_name or user.username.split("@")[0],
                "email": user.email,
                "username": user.username,
                "yearLevel": profile.year_level,
                "role": profile.role,
            },
            "redirect": _redirect_for_role(profile.role),
        }
    )


@csrf_exempt
@api_view(["POST"])
def verify_email(request: Any) -> Response:
    email = str(request.data.get("email") or request.query_params.get("email") or "").strip().lower()
    otp = str(request.data.get("otp") or request.query_params.get("otp") or "").strip()
    if not email or not otp:
        return Response({"error": "Missing email or otp"}, status=400)

    try:
        user = User.objects.get(username=email)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    # Find latest valid OTP
    now = timezone.now()
    latest = EmailOTP.objects.filter(user=user, expires_at__gte=now).order_by("-created_at").first()
    if not latest:
        return Response({"error": "No valid verification code found. Request a new one."}, status=400)

    if latest.otp != otp:
        # increment attempts
        latest.attempts = (latest.attempts or 0) + 1
        latest.save(update_fields=["attempts"])  # type: ignore[arg-type]
        return Response({"error": "Invalid verification code"}, status=400)

    # valid OTP
    user.is_active = True
    user.save(update_fields=["is_active"])  # type: ignore[arg-type]

    # cleanup otps for user
    EmailOTP.objects.filter(user=user).delete()

    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            "full_name": user.first_name or user.username.split("@")[0],
            "role": "student",
            "year_level": "",
        },
    )
    _get_learning_state_for_user(user)

    return Response({"message": "Email verified. You can now log in."})


@csrf_exempt
@api_view(["POST"])
def resend_verification(request: Any) -> Response:
    email = str(request.data.get("email") or request.query_params.get("email") or "").strip().lower()
    if not email:
        return Response({"error": "Missing email"}, status=400)
    try:
        user = User.objects.get(username=email)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    if user.is_active:
        return Response({"message": "Email already verified"})

    # Avoid duplicate sends when the resend button is clicked repeatedly or the client retries.
    now = timezone.now()
    recent_otp = (
        EmailOTP.objects.filter(user=user, expires_at__gte=now, created_at__gte=now - timedelta(seconds=60))
        .order_by("-created_at")
        .first()
    )
    if recent_otp:
        return Response({"message": "A verification code was already sent recently. Please check your email."})

    result = _create_and_send_otp(user, request)
    if not result.get("ok"):
        # In development include error details so frontend can surface them.
        details = result.get("error")
        return Response({
            "message": "Failed to send verification code.",
            "error": "email_delivery_failed",
            "details": details,
        }, status=500)

    return Response({"message": "Verification code sent."})


@csrf_exempt
@api_view(["POST"])
def request_password_reset(request: Any) -> Response:
    email = str(request.data.get("email") or request.query_params.get("email") or "").strip().lower()
    if not email:
        return Response({"error": "Missing email"}, status=400)
    user = _find_user_by_identifier(email)
    if not user:
        return Response({"error": "User not found"}, status=404)

    result = _create_and_send_otp(user, request, purpose="password_reset")
    if not result.get("ok"):
        details = result.get("error")
        return Response({
            "message": "Failed to send password reset code.",
            "error": "email_delivery_failed",
            "details": details,
        }, status=500)

    return Response({
        "message": "Password reset code sent to your email.",
        "redirect": f"reset-password.html?email={email}",
    })


@csrf_exempt
@api_view(["POST"])
def resend_password_reset_code(request: Any) -> Response:
    email = str(request.data.get("email") or request.query_params.get("email") or "").strip().lower()
    if not email:
        return Response({"error": "Missing email"}, status=400)
    user = _find_user_by_identifier(email)
    if not user:
        return Response({"error": "User not found"}, status=404)

    now = timezone.now()
    recent_otp = (
        EmailOTP.objects.filter(user=user, expires_at__gte=now, created_at__gte=now - timedelta(seconds=60))
        .order_by("-created_at")
        .first()
    )
    if recent_otp:
        return Response({"message": "A reset code was already sent recently. Please check your email."})

    result = _create_and_send_otp(user, request, purpose="password_reset")
    if not result.get("ok"):
        details = result.get("error")
        return Response({
            "message": "Failed to send password reset code.",
            "error": "email_delivery_failed",
            "details": details,
        }, status=500)

    return Response({"message": "Password reset code sent."})


@csrf_exempt
@api_view(["POST"])
def reset_password(request: Any) -> Response:
    email = str(request.data.get("email") or request.query_params.get("email") or "").strip().lower()
    otp = str(request.data.get("otp") or request.query_params.get("otp") or "").strip()
    new_password = str(request.data.get("newPassword") or "").strip()
    confirm_password = str(request.data.get("confirmPassword") or "").strip()

    if not email or not otp or not new_password or not confirm_password:
        return Response({"error": "Email, reset code, and new passwords are required."}, status=400)
    if new_password != confirm_password:
        return Response({"error": "Passwords do not match"}, status=400)
    if len(new_password) < 8:
        return Response({"error": "Password must be at least 8 characters long"}, status=400)

    user = _find_user_by_identifier(email)
    if not user:
        return Response({"error": "User not found"}, status=404)

    now = timezone.now()
    latest = EmailOTP.objects.filter(user=user, expires_at__gte=now).order_by("-created_at").first()
    if not latest:
        return Response({"error": "No valid reset code found. Request a new one."}, status=400)
    if latest.otp != otp:
        latest.attempts = (latest.attempts or 0) + 1
        latest.save(update_fields=["attempts"])
        return Response({"error": "Invalid reset code"}, status=400)

    user.set_password(new_password)
    user.save(update_fields=["password"])
    EmailOTP.objects.filter(user=user).delete()

    return Response({"message": "Password reset successfully. You can now log in."})


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
        data = LearningStateSerializer(user_learning_state).data
        presented_state = dict(user_learning_state.state or {})
        presented_state["performance"] = _skill_breakdown_for_user(user)
        presented_state["achievements"] = _evaluate_achievements(user, presented_state)
        data["state"] = presented_state
        return Response(data)

    state = request.data.get("state")
    if not isinstance(state, dict):
        return Response({"error": "state must be an object"}, status=400)

    user_learning_state.state = state
    user_learning_state.save(update_fields=["state", "updated_at"])
    serializer = LearningStateSerializer(user_learning_state)
    return Response(serializer.data)


@api_view(["GET"])
def student_content(request: Any) -> Response:
    email = str(request.query_params.get("email") or "").strip().lower()
    if not email:
        return Response({"error": "Missing email"}, status=400)

    try:
        user = User.objects.select_related("profile").get(username=email)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    profile = getattr(user, "profile", None)
    own_year_level = str(getattr(profile, "year_level", "1") or "1").strip()
    year_level = _normalize_year_level_filter(request.query_params.get("yearLevel"))

    try:
        page = max(1, int(request.query_params.get("page") or 1))
    except Exception:
        page = 1
    try:
        limit = max(1, min(50, int(request.query_params.get("limit") or 10)))
    except Exception:
        limit = 10

    # Return published modules for all year levels, optionally narrowed to one
    # via the ?yearLevel= query param, with attached files.
    modules_qs = (
        LearningModule.objects
        .select_related("created_by", "updated_by")
        .prefetch_related("files", "quiz_questions")
        .filter(status=LearningModule.STATUS_PUBLISHED)
        .order_by("year_level", "sort_order", "title")
    )
    if year_level != "all":
        modules_qs = modules_qs.filter(year_level=year_level)
    total = modules_qs.count()
    start = (page - 1) * limit
    end = start + limit
    modules = list(modules_qs[start:end])

    serialized = []
    for module in modules:
        module_data = LearningModuleSerializer(module).data
        module_files = list(module.files.all().order_by("-created_at"))
        module_data["files"] = ModuleFileSerializer(module_files, many=True, context={"request": request}).data
        # include quiz count and student-safe quiz payload
        questions = list(module.quiz_questions.all().order_by("order", "created_at"))
        module_data["quizCount"] = len(questions)
        module_data["quizzes"] = StudentQuizQuestionSerializer(questions, many=True).data
        serialized.append(module_data)

    return Response({
        "modules": serialized,
        "total": total,
        "page": page,
        "limit": limit,
        "yearLevel": year_level,
        "ownYearLevel": own_year_level,
    })


def _request_email(request: Any) -> str:
    query_email = (
        request.query_params.get("actorEmail")
        or request.query_params.get("adminEmail")
        or request.query_params.get("instructorEmail")
        or request.query_params.get("email")
        or ""
    )
    body_email = (
        request.data.get("actorEmail")
        or request.data.get("adminEmail")
        or request.data.get("instructorEmail")
        or request.data.get("email")
        or ""
    )
    return str(query_email or body_email).strip().lower()


def _get_instructor_actor(request: Any):
    email = _request_email(request)
    logger.info(f"[DEBUG] _get_instructor_actor: request.method={request.method}, request.data={request.data}, query_params={request.query_params}, extracted_email={email}")
    if not email:
        logger.error(f"[DEBUG] No email found in request data: {request.data} or query_params: {request.query_params}")
        return None, Response({"error": "Missing instructor email"}, status=400)

    try:
        # Try to find by email first, then by username
        user = User.objects.select_related("profile").get(email=email)
    except User.DoesNotExist:
        try:
            user = User.objects.select_related("profile").get(username=email)
        except User.DoesNotExist:
            return None, Response({"error": "User not found"}, status=404)

    profile = getattr(user, "profile", None)
    if not profile or profile.role not in {"instructor", "admin"}:
        return None, Response({"error": "Instructor access required"}, status=403)

    # Deny access if instructor/admin account has been marked inactive (1 == inactive)
    if getattr(profile, "active", 0) == 1:
        return None, Response({"error": "Instructor account is inactive"}, status=403)

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


def _serialize_student_row(learning_state: UserLearningState, total_modules: int, request: Any = None) -> dict:
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
        **(_profile_avatar_payload(profile, request) if request is not None else {"photoUrl": "", "avatarId": ""}),
    }


def _student_learning_state(user: User) -> UserLearningState | None:
    return UserLearningState.objects.filter(user=user).first()


def _serialize_user_profile_row(profile: UserProfile, request: Any = None) -> dict:
    user = profile.user
    return {
        "id": user.id,
        "name": profile.full_name or user.first_name or user.username,
        "email": user.email,
        "username": user.username,
        "role": str(profile.role or "student").lower(),
        "yearLevel": str(profile.year_level or ""),
        "active": _safe_int(getattr(profile, "active", 0), 0),
        "createdAt": profile.created_at.isoformat() if profile.created_at else "",
        **(_profile_avatar_payload(profile, request) if request is not None else {"photoUrl": "", "avatarId": ""}),
    }


def _get_admin_actor(request: Any):
    actor, error_response = _get_instructor_actor(request)
    if error_response:
        return None, error_response

    profile = getattr(actor, "profile", None)
    if not profile or str(profile.role or "").lower() != "admin":
        return None, Response({"error": "Admin access required"}, status=403)

    return actor, None


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
        page = max(1, int(request.query_params.get("page") or 1))
    except Exception:
        page = 1
    try:
        page_size = max(1, min(50, int(request.query_params.get("pageSize") or 10)))
    except Exception:
        page_size = 10

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
        student_row = _serialize_student_row(learning_state, total_modules, request)
        total_points += student_row["points"]
        total_completion += student_row["overallProgress"]
        if student_row["points"] > 0 or student_row["modulesCompleted"] > 0:
            active_students += 1
        students.append(student_row)

    students.sort(key=lambda item: (item["points"], item["overallProgress"], item["accuracy"]), reverse=True)

    total_students = len(students)
    start = (page - 1) * page_size
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
                "files": ModuleFileSerializer(
                    list(module.files.all().order_by("-created_at")),
                    many=True,
                    context={"request": request},
                ).data,
                "studentCount": module_counts.get(module.module_key, 0),
                "quizCount": module.quiz_questions.count(),
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

    actor_profile = getattr(actor, "profile", None)
    if actor_profile and str(getattr(actor_profile, "role", "")).lower() == "admin":
        all_profiles = list(UserProfile.objects.select_related("user").order_by("role", "full_name", "user__username"))
        payload["users"] = [_serialize_user_profile_row(profile, request) for profile in all_profiles]
        payload["roleCounts"] = {
            "student": sum(1 for profile in all_profiles if str(profile.role or "").lower() == "student"),
            "instructor": sum(1 for profile in all_profiles if str(profile.role or "").lower() == "instructor"),
            "admin": sum(1 for profile in all_profiles if str(profile.role or "").lower() == "admin"),
            "total": len(all_profiles),
            "inactive": sum(1 for profile in all_profiles if _safe_int(getattr(profile, "active", 0), 0) == 1),
        }

    return Response(payload)


@api_view(["GET", "POST"])
def admin_users(request: Any) -> Response:
    actor, error_response = _get_admin_actor(request)
    if error_response:
        return error_response

    # If POST, create a new user (admin action)
    if request.method == "POST":
        payload = request.data.copy() if isinstance(request.data, dict) else {}
        email = str(payload.get("email") or "").strip().lower()
        first_name = _normalize_name_part(payload.get("firstName") or "")
        middle_name = _normalize_name_part(payload.get("middleName") or "")
        last_name = _normalize_name_part(payload.get("lastName") or "")
        suffix = _normalize_name_part(payload.get("suffix") or "")
        password = str(payload.get("password") or "")
        year_level = str(payload.get("yearLevel") or "").strip()
        role = str(payload.get("role") or "instructor").strip().lower()

        if not email:
            return Response({"error": "Email is required"}, status=400)
        if User.objects.filter(username=email).exists():
            return Response({"error": "Email is already registered"}, status=409)
        if not password or len(password) < 8:
            return Response({"error": "Password must be at least 8 characters"}, status=400)
        if not first_name or not last_name:
            return Response({"error": "First name and last name are required"}, status=400)

        if role not in {"student", "instructor", "admin"}:
            role = "instructor"

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        full_name = " ".join([part for part in [first_name, middle_name, last_name, suffix] if part]).strip()

        profile = UserProfile.objects.create(
            user=user,
            full_name=full_name,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            suffix=suffix,
            year_level=year_level,
            role=role,
            security_pin="",
        )

        _get_learning_state_for_user(user)

        return Response({"message": "User created", "user": _serialize_user_profile_row(profile, request)}, status=201)

    role_filter = str(request.query_params.get("role") or "all").strip().lower()
    try:
        page = max(1, int(request.query_params.get("page") or 1))
    except Exception:
        page = 1
    try:
        page_size = max(1, min(50, int(request.query_params.get("pageSize") or 10)))
    except Exception:
        page_size = 10

    profiles_qs = UserProfile.objects.select_related("user").all().order_by("role", "full_name", "user__username")
    if role_filter in {"student", "instructor", "admin"}:
        profiles_qs = profiles_qs.filter(role=role_filter)

    total = profiles_qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    profiles = list(profiles_qs[start:end])
    return Response(
        {
            "currentUser": {
                "email": actor.email,
                "role": "admin",
            },
            "users": [_serialize_user_profile_row(profile, request) for profile in profiles],
            "role": role_filter,
            "total": total,
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "totalPages": max(1, (total + page_size - 1) // page_size),
            },
        }
    )


@api_view(["PATCH"])
def admin_user_status(request: Any, user_id: int) -> Response:
    actor, error_response = _get_admin_actor(request)
    if error_response:
        return error_response

    target_profile = get_object_or_404(UserProfile.objects.select_related("user"), user_id=user_id)

    if target_profile.user_id == actor.id:
        return Response({"error": "You cannot deactivate your own admin account"}, status=400)

    next_active = _safe_int(request.data.get("active"), -1)
    if next_active not in {0, 1}:
        return Response({"error": "active must be 0 (active) or 1 (inactive)"}, status=400)

    target_profile.active = next_active
    target_profile.save(update_fields=["active"])

    return Response({
        "message": "User status updated",
        "user": _serialize_user_profile_row(target_profile, request),
    })


@api_view(["PATCH"])
def admin_user_details(request: Any, user_id: int) -> Response:
    actor, error_response = _get_admin_actor(request)
    if error_response:
        return error_response

    target_profile = get_object_or_404(UserProfile.objects.select_related("user"), user_id=user_id)
    target_user = target_profile.user

    # Extract fields from request
    full_name = _normalize_name_part(request.data.get("name") or "")
    email = str(request.data.get("email") or "").strip().lower()
    role = str(request.data.get("role") or "").strip().lower()
    year_level = str(request.data.get("yearLevel") or "").strip()

    # Track changes
    user_updated = False
    profile_updated = False

    # Validate and update email
    if email and email != target_user.email:
        if User.objects.filter(email=email).exclude(id=target_user.id).exists():
            return Response({"error": "Email already in use"}, status=400)
        target_user.email = email
        user_updated = True

    # Validate and update role
    if role and role not in {"student", "instructor", "admin"}:
        return Response({"error": f"Invalid role: {role}"}, status=400)
    if role and role != str(target_profile.role or "").lower():
        target_profile.role = role
        profile_updated = True

    # Update other fields
    if full_name and full_name != (target_profile.full_name or ""):
        target_profile.full_name = full_name
        profile_updated = True

    if year_level and year_level != str(target_profile.year_level or ""):
        target_profile.year_level = year_level
        profile_updated = True

    # Save changes
    if user_updated:
        target_user.save(update_fields=["email"])
    if profile_updated:
        target_profile.save()

    return Response({
        "message": "User details updated",
        "user": _serialize_user_profile_row(target_profile, request),
    })


@api_view(["GET", "POST"])
def instructor_modules(request: Any) -> Response:
    actor, error_response = _get_instructor_actor(request)
    if error_response:
        return error_response

    if request.method == "GET":
        try:
            modules_qs = LearningModule.objects.select_related("created_by", "updated_by").prefetch_related("files", "quiz_questions").order_by("sort_order", "title").all()
            year_level = _normalize_year_level_filter(request.query_params.get("yearLevel"))
            if year_level != "all":
                modules_qs = modules_qs.filter(year_level=year_level)
            try:
                page = max(1, int(request.query_params.get("page") or 1))
            except Exception:
                page = 1
            try:
                limit = max(1, min(100, int(request.query_params.get("limit") or 50)))
            except Exception:
                limit = 50

            total = modules_qs.count()
            start = (page - 1) * limit
            end = start + limit
            modules = list(modules_qs[start:end])
            module_counts = _module_student_counts(list(modules))
            return Response({
                "modules": [
                    {
                        **LearningModuleSerializer(module).data,
                        "files": ModuleFileSerializer(
                            list(module.files.all().order_by("-created_at")),
                            many=True,
                            context={"request": request},
                        ).data,
                        "studentCount": module_counts.get(module.module_key, 0),
                        "quizCount": module.quiz_questions.count(),
                    }
                    for module in modules
                ],
                "total": total,
                "page": page,
                "limit": limit,
                "yearLevel": year_level,
            })
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
    response_data["files"] = []
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
        data["files"] = ModuleFileSerializer(list(module.files.all().order_by("-created_at")), many=True, context={"request": request}).data
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
def module_quiz_questions(request: Any, module_id: int) -> Response:
    actor, error_response = _get_instructor_actor(request)
    if error_response:
        return error_response

    module = get_object_or_404(LearningModule, pk=module_id)

    if request.method == "GET":
        questions = QuizQuestion.objects.filter(module=module).order_by("order", "created_at")
        return Response(QuizQuestionSerializer(questions, many=True).data)

    payload = request.data.copy()
    serializer = QuizQuestionSerializer(data={
        "module": module.id,
        "question_text": str(payload.get("question_text") or "").strip(),
        "question_type": str(payload.get("question_type") or QuizQuestion.QUESTION_TYPE_MULTIPLE_CHOICE).strip(),
        "choices": payload.get("choices") or [],
        "correct_answer": str(payload.get("correct_answer") or "").strip(),
        "order": int(payload.get("order") or 0),
    })
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=400)

    question = serializer.save()
    return Response(QuizQuestionSerializer(question).data, status=201)


@api_view(["POST"])
def module_quiz_submit(request: Any, module_id: int) -> Response:
    """Endpoint for students to submit quiz answers for grading.

    Expects JSON: { "email": "student@example.com", "answers": [{"question_id": 1, "answer": "A"}, ...] }
    Returns: { score: int, total: int, details: [{question_id, correct, expected, given}] }
    """
    email = str(request.data.get("email") or request.query_params.get("email") or "").strip().lower()
    answers = request.data.get("answers") or []

    try:
        module = LearningModule.objects.get(pk=module_id)
    except LearningModule.DoesNotExist:
        return Response({"error": "Module not found"}, status=404)

    # Build lookup of correct answers
    questions = list(QuizQuestion.objects.filter(module=module).all())
    question_map = {q.id: q for q in questions}

    if not isinstance(answers, list):
        return Response({"error": "answers must be a list"}, status=400)

    details = []
    correct_count = 0
    for ans in answers:
        try:
            qid = int(ans.get("question_id"))
        except Exception:
            continue
        given = ans.get("answer")
        q = question_map.get(qid)
        if not q:
            details.append({"question_id": qid, "correct": False, "expected": None, "given": given})
            continue
        expected = str(q.correct_answer or "").strip()
        # Compare normalized strings for simple grading
        is_correct = False
        if expected != "":
            try:
                is_correct = str(given or "").strip().lower() == expected.strip().lower()
            except Exception:
                is_correct = False

        if is_correct:
            correct_count += 1

        details.append({"question_id": qid, "correct": bool(is_correct), "expected": expected, "given": given})

    total = len(questions)
    score = correct_count

    # Any submission completes the module, regardless of score, and updates
    # the student's progress/recent-activity state authoritatively here so
    # completion is guaranteed correct even if the client never re-syncs.
    updated_state = None
    if email:
        try:
            user = User.objects.get(username=email)
        except User.DoesNotExist:
            user = None

        if user is not None:
            try:
                QuizAttempt.objects.create(user=user, module=module, score=score, total=total)

                learning_state = _get_learning_state_for_user(user)
                state = dict(learning_state.state or {})
                module_progress = dict(state.get("moduleProgress") or {})
                module_progress[module.module_key] = 100
                state["moduleProgress"] = module_progress

                state["points"] = int(state.get("points") or 0) + 50
                state["completedActivities"] = int(state.get("completedActivities") or 0) + 1

                recent_activity = list(state.get("recentActivity") or [])
                recent_activity.insert(0, {
                    "icon": "📝",
                    "text": f"Completed quiz: {module.title}",
                    "meta": f"{score}/{total} correct",
                })
                state["recentActivity"] = recent_activity[:10]

                state["performance"] = _skill_breakdown_for_user(user)
                state["achievements"] = _evaluate_achievements(user, state)

                learning_state.state = state
                learning_state.save(update_fields=["state", "updated_at"])
                updated_state = state
            except Exception:
                logger.exception("Failed to persist quiz completion state for %s / module %s", email, module_id)

    return Response({"score": score, "total": total, "details": details, "state": updated_state})


@api_view(["PATCH", "DELETE"])
def module_quiz_question_detail(request: Any, module_id: int, question_id: int) -> Response:
    actor, error_response = _get_instructor_actor(request)
    if error_response:
        return error_response

    module = get_object_or_404(LearningModule, pk=module_id)
    question = get_object_or_404(QuizQuestion, pk=question_id, module=module)

    if request.method == "DELETE":
        question.delete()
        return Response({"message": "Question deleted"})

    payload = request.data.copy()
    update_data = {
        "question_text": str(payload.get("question_text") or question.question_text).strip(),
        "question_type": str(payload.get("question_type") or question.question_type).strip(),
        "choices": payload.get("choices") if payload.get("choices") is not None else question.choices,
        "correct_answer": str(payload.get("correct_answer") or question.correct_answer).strip(),
        "order": int(payload.get("order") or question.order),
    }
    serializer = QuizQuestionSerializer(question, data=update_data, partial=True)
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=400)

    question = serializer.save()
    return Response(QuizQuestionSerializer(question).data)


@api_view(["GET"])
def check_session(request: Any) -> Response:
    """Check if user is authenticated via session cookie."""
    if not request.user.is_authenticated:
        return Response({"authenticated": False, "user": None}, status=401)

    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(
            user=request.user,
            full_name=request.user.first_name or request.user.username.split("@")[0],
            role="student",
        )

    return Response({
        "authenticated": True,
        "user": {
            "id": request.user.id,
            "name": profile.full_name or request.user.first_name or request.user.username.split("@")[0],
            "email": request.user.email,
            "username": request.user.username,
            **_profile_avatar_payload(profile, request),
            "firstName": profile.first_name or request.user.first_name or "",
            "middleName": profile.middle_name or "",
            "lastName": profile.last_name or request.user.last_name or "",
            "suffix": profile.suffix or "",
            "yearLevel": profile.year_level,
            "role": profile.role,
            "studentId": profile.student_id or "",
            "contactNumber": profile.contact_number or "",
            "hearingStatus": profile.hearing_status or "",
        }
    })


@ensure_csrf_cookie
@api_view(["GET"])
def csrf_token(request: Any) -> Response:
    """Set the CSRF cookie for browser clients that submit session-backed POST requests.

    Also returns the real token in the response body: browsers that block
    third-party cookies (Safari ITP, Chrome/Firefox cross-site restrictions)
    silently drop the cross-site csrftoken cookie set here, so the frontend
    cannot read it back via document.cookie. Returning the token in the JSON
    body lets the frontend send it as the X-CSRFToken header even when the
    cookie itself never lands in the browser's cookie jar.
    """
    from django.middleware.csrf import get_token
    return Response({"csrfToken": get_token(request)})


@csrf_exempt
@api_view(["POST"])
def logout(request: Any) -> Response:
    """Log out the user by clearing the session."""
    from django.contrib.auth import logout as django_logout
    django_logout(request)
    return Response({"message": "Logged out successfully"})



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
def instructor_game_levels(request: Any) -> Response:
    actor, error_response = _get_instructor_actor(request)
    if error_response:
        return error_response

    if request.method == "GET":
        levels = GameLevel.objects.select_related("created_by", "updated_by").prefetch_related("items").all()
        game_key = request.query_params.get("game_key")
        if game_key:
            levels = levels.filter(game_key=game_key)
        return Response(GameLevelSerializer(levels, many=True).data)

    serializer = GameLevelSerializer(data={
        "game_key": str(request.data.get("game_key") or "").strip(),
        "difficulty": str(request.data.get("difficulty") or GameLevel.DIFFICULTY_EASY).strip(),
        "level_number": int(request.data.get("level_number") or 1),
        "title": str(request.data.get("title") or "").strip(),
        "is_published": _safe_bool(request.data.get("is_published", True), True),
    })
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=400)

    level = serializer.save(created_by=actor, updated_by=actor)
    return Response(GameLevelSerializer(level).data, status=201)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
def instructor_game_level_detail(request: Any, level_id: int) -> Response:
    actor, error_response = _get_instructor_actor(request)
    if error_response:
        return error_response

    level = get_object_or_404(GameLevel, pk=level_id)

    if request.method == "GET":
        return Response(GameLevelSerializer(level).data)

    if request.method == "DELETE":
        level.delete()
        return Response({"message": "Level deleted"})

    serializer = GameLevelSerializer(
        level,
        data={
            "game_key": str(request.data.get("game_key") or level.game_key).strip(),
            "difficulty": str(request.data.get("difficulty") or level.difficulty).strip(),
            "level_number": int(request.data.get("level_number") or level.level_number),
            "title": str(request.data.get("title") if request.data.get("title") is not None else level.title).strip(),
            "is_published": _safe_bool(request.data.get("is_published", level.is_published), level.is_published),
        },
        partial=True,
    )
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=400)

    level = serializer.save(updated_by=actor)
    return Response(GameLevelSerializer(level).data)


@api_view(["GET", "POST"])
def game_level_items(request: Any, level_id: int) -> Response:
    actor, error_response = _get_instructor_actor(request)
    if error_response:
        return error_response

    level = get_object_or_404(GameLevel, pk=level_id)

    if request.method == "GET":
        items = GameLevelItem.objects.filter(level=level).order_by("order", "id")
        return Response(GameLevelItemSerializer(items, many=True).data)

    payload = request.data.copy()
    serializer = GameLevelItemSerializer(data={
        "level": level.id,
        "prompt": str(payload.get("prompt") or "").strip(),
        "answer": str(payload.get("answer") or "").strip(),
        "media_url": str(payload.get("media_url") or "").strip(),
        "extra_data": payload.get("extra_data") or {},
        "order": int(payload.get("order") or 0),
    })
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=400)

    item = serializer.save()
    return Response(GameLevelItemSerializer(item).data, status=201)


@api_view(["PATCH", "DELETE"])
def game_level_item_detail(request: Any, level_id: int, item_id: int) -> Response:
    actor, error_response = _get_instructor_actor(request)
    if error_response:
        return error_response

    level = get_object_or_404(GameLevel, pk=level_id)
    item = get_object_or_404(GameLevelItem, pk=item_id, level=level)

    if request.method == "DELETE":
        item.delete()
        return Response({"message": "Item deleted"})

    payload = request.data.copy()
    serializer = GameLevelItemSerializer(
        item,
        data={
            "level": level.id,
            "prompt": str(payload.get("prompt") if payload.get("prompt") is not None else item.prompt).strip(),
            "answer": str(payload.get("answer") if payload.get("answer") is not None else item.answer).strip(),
            "media_url": str(payload.get("media_url") if payload.get("media_url") is not None else item.media_url).strip(),
            "extra_data": payload.get("extra_data") if payload.get("extra_data") is not None else item.extra_data,
            "order": int(payload.get("order") or item.order),
        },
        partial=True,
    )
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=400)

    item = serializer.save()
    return Response(GameLevelItemSerializer(item).data)


@api_view(["GET"])
def public_game_levels(request: Any, game_key: str) -> Response:
    """Public listing of published levels (with content) for a game.

    Consumed directly by the student-facing game pages so teacher-authored
    levels replace each game's default pool once published.
    """
    valid_game_keys = {choice[0] for choice in GameLevel.GAME_CHOICES}
    if game_key not in valid_game_keys:
        return Response({"error": f"Invalid game_key: {game_key}"}, status=400)

    levels = GameLevel.objects.filter(game_key=game_key, is_published=True).prefetch_related("items")
    difficulty = str(request.query_params.get("difficulty") or "").strip().lower()
    if difficulty:
        levels = levels.filter(difficulty=difficulty)
    return Response(GameLevelSerializer(levels, many=True).data)


@api_view(["POST"])
def instructor_upload_sign_video(request: Any) -> Response:
    """Instructor upload of a sign video for use as Game Level content.

    Creates a SignVideo (text_to_sign_only=False) so it's immediately usable
    through the shared /sign-videos/?scope=games pool the games already read.
    Re-uploading an existing word/phrase reuses the existing video instead of
    erroring, since teachers commonly reuse the same word across levels.
    """
    actor, error_response = _get_instructor_actor(request)
    if error_response:
        return error_response

    word = str(request.data.get("word") or "").strip()
    if not word:
        return Response({"error": "Word/phrase is required"}, status=400)

    key = _key_for_word(word)
    existing = SignVideo.objects.filter(key=key).first()
    if existing:
        return Response(AdminSignVideoSerializer(existing, context={"request": request}).data)

    if "video" not in request.FILES:
        return Response({"error": "No video file provided"}, status=400)

    category = str(request.data.get("category") or SignVideo.CATEGORY_PHRASES).strip().lower()
    valid_categories = {choice[0] for choice in SignVideo.CATEGORY_CHOICES}
    if category not in valid_categories:
        category = SignVideo.CATEGORY_PHRASES

    try:
        video = SignVideo.objects.create(
            key=key,
            word=word,
            category=category,
            video=request.FILES["video"],
            order=_safe_int(request.data.get("order"), 0),
            is_published=True,
            text_to_sign_only=False,
        )
        return Response(AdminSignVideoSerializer(video, context={"request": request}).data, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=400)


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


@api_view(["GET"])
def sign_videos(request: Any) -> Response:
    """Public listing of sign language demonstration videos.

    Shared data source for the Games and Text-to-Sign modules -- both read
    from the SignVideo table instead of hardcoded local video files. Pass
    ?scope=games to exclude videos uploaded via the Admin "Sign Language
    Videos" manager, which are meant for Text-to-Sign only.
    """
    videos = SignVideo.objects.filter(is_published=True).order_by("category", "order", "word")
    category = str(request.query_params.get("category") or "").strip().lower()
    if category:
        videos = videos.filter(category=category)
    scope = str(request.query_params.get("scope") or "").strip().lower()
    if scope == "games":
        videos = videos.exclude(text_to_sign_only=True)
    return Response(SignVideoSerializer(videos, many=True, context={"request": request}).data)


def _key_for_word(word: str) -> str:
    return str(word or "").strip().lower()


@api_view(["GET", "POST"])
def admin_sign_videos(request: Any) -> Response:
    """Admin management of Text-to-Sign videos: list all, or upload a new one."""
    actor, error_response = _get_admin_actor(request)
    if error_response:
        return error_response

    if request.method == "GET":
        videos = SignVideo.objects.all().order_by("category", "order", "word")
        category = str(request.query_params.get("category") or "").strip().lower()
        if category:
            videos = videos.filter(category=category)
        return Response(AdminSignVideoSerializer(videos, many=True, context={"request": request}).data)

    # POST - upload a new video. Always scoped to Text-to-Sign only.
    word = str(request.data.get("word") or "").strip()
    if not word:
        return Response({"error": "Word/phrase is required"}, status=400)

    if "video" not in request.FILES:
        return Response({"error": "No video file provided"}, status=400)

    category = str(request.data.get("category") or SignVideo.CATEGORY_PHRASES).strip().lower()
    valid_categories = {choice[0] for choice in SignVideo.CATEGORY_CHOICES}
    if category not in valid_categories:
        return Response({"error": f"Invalid category: {category}"}, status=400)

    key = _key_for_word(word)
    if SignVideo.objects.filter(key=key).exists():
        return Response({"error": "A video for this word/phrase already exists"}, status=409)

    try:
        video = SignVideo.objects.create(
            key=key,
            word=word,
            category=category,
            video=request.FILES["video"],
            order=_safe_int(request.data.get("order"), 0),
            is_published=_safe_bool(request.data.get("is_published"), True),
            text_to_sign_only=True,
        )
        return Response(AdminSignVideoSerializer(video, context={"request": request}).data, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(["GET", "PATCH", "DELETE"])
def admin_sign_video_detail(request: Any, video_id: int) -> Response:
    """Admin get/update/delete of a single Text-to-Sign video."""
    actor, error_response = _get_admin_actor(request)
    if error_response:
        return error_response

    video = get_object_or_404(SignVideo, pk=video_id)

    if request.method == "GET":
        return Response(AdminSignVideoSerializer(video, context={"request": request}).data)

    if request.method == "DELETE":
        if video.video:
            video.video.delete(save=False)
        video.delete()
        return Response({"message": "Video deleted"})

    # PATCH - update fields and optionally replace the video file.
    word = str(request.data.get("word") or video.word).strip()
    if not word:
        return Response({"error": "Word/phrase is required"}, status=400)

    category = str(request.data.get("category") or video.category).strip().lower()
    valid_categories = {choice[0] for choice in SignVideo.CATEGORY_CHOICES}
    if category not in valid_categories:
        return Response({"error": f"Invalid category: {category}"}, status=400)

    if word != video.word:
        new_key = _key_for_word(word)
        if SignVideo.objects.exclude(pk=video.pk).filter(key=new_key).exists():
            return Response({"error": "A video for this word/phrase already exists"}, status=409)
        video.key = new_key
        video.word = word

    video.category = category
    video.order = _safe_int(request.data.get("order"), video.order)
    if "is_published" in request.data:
        video.is_published = _safe_bool(request.data.get("is_published"), video.is_published)

    if "video" in request.FILES:
        if video.video:
            video.video.delete(save=False)
        video.video = request.FILES["video"]

    video.save()
    return Response(AdminSignVideoSerializer(video, context={"request": request}).data)


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
