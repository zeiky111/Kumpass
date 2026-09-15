import os
import re

from django.conf import settings
from rest_framework import serializers

from .models import (
    Announcement,
    GameLevel,
    GameLevelItem,
    LearningModule,
    ModuleFile,
    QuizQuestion,
    SignPredictionLog,
    SignVideo,
    UserLearningState,
)


class SignPredictionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignPredictionLog
        fields = ["id", "prediction", "confidence", "source", "created_at"]


class SignupSerializer(serializers.Serializer):
    firstName = serializers.CharField(max_length=64)
    middleName = serializers.CharField(max_length=64, required=False, allow_blank=True)
    lastName = serializers.CharField(max_length=64)
    suffix = serializers.CharField(max_length=32, required=False, allow_blank=True)
    email = serializers.EmailField()
    yearLevel = serializers.CharField(max_length=20, required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, max_length=128)
    confirmPassword = serializers.CharField(min_length=8, max_length=128)
    # Public signup only supports student accounts; role and PIN are managed by admins/setup


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128)
    # Login accepts email or username plus password


class LearningStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLearningState
        fields = ["id", "state", "created_at", "updated_at"]


class LearningModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningModule
        fields = [
            "id",
            "module_key",
            "title",
            "year_level",
            "description",
            "activities_count",
            "status",
            "sort_order",
            "created_at",
            "updated_at",
        ]


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ["id", "title", "message", "is_published", "created_at", "updated_at"]


class ModuleFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ModuleFile
        fields = [
            "id",
            "module",
            "file_name",
            "file",
            "file_url",
            "file_type",
            "file_size",
            "description",
            "created_at",
        ]

    def get_file_url(self, obj):
        """Get the full URL for the file"""
        request = self.context.get("request")
        if obj.file and hasattr(obj.file, "url"):
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class QuizQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizQuestion
        fields = [
            "id",
            "module",
            "question_text",
            "question_type",
            "choices",
            "correct_answer",
            "order",
            "created_at",
            "updated_at",
        ]


def _normalize_word_key(value):
    cleaned = re.sub(r"[^a-z0-9\s']", " ", str(value or "").lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _local_media_path_exists(relative_name):
    """Cheap on-disk check (no network) against MEDIA_ROOT."""
    if not relative_name:
        return False
    try:
        return os.path.isfile(os.path.join(settings.MEDIA_ROOT, relative_name))
    except Exception:
        return False


def _resolve_local_relative_name(video):
    """Finds the actual on-disk filename for a SignVideo row.

    SignVideo.video.name is itself sometimes wrong: the FSL-105 import
    saved each clip through Django's storage API, which appends a random
    suffix (e.g. "fsl105_april_qpiwLrj.mp4") whenever it detects a naming
    collision -- but that particular suffixed file was never actually
    persisted anywhere (not locally, not on Cloudinary), only the plain
    "fsl105_april.mp4" from the original import is real, and it's what's
    committed under backend/media/. Falls back to reconstructing that clean
    name (<key>.mp4, same folder) when the stored name doesn't check out.
    """
    stored_name = getattr(video.video, "name", "") or ""
    if _local_media_path_exists(stored_name):
        return stored_name

    if video.key:
        directory = os.path.dirname(stored_name) if stored_name else "sign_videos"
        candidate = f"{directory}/{video.key}.mp4" if directory else f"{video.key}.mp4"
        if _local_media_path_exists(candidate):
            return candidate

    return None


def build_sign_video_lookup(request=None):
    """Maps normalized word -> current video URL, built fresh from SignVideo.

    GameLevelItem.media_url (and each extra_data.pool entry's media_url) is a
    plain string frozen at whatever moment a past migration/import wrote it --
    Render's disk is ephemeral, so once that exact file is gone (wiped on a
    later deploy, or replaced by a differently-named re-upload), the frozen
    path 404s forever even though the same word's video still exists in
    SignVideo, just under a different path.

    Prefers serving straight from Django's local /media/ (checked against
    disk, not trusted blindly) over SignVideo.video.url: the actual video
    bytes for these words are committed under backend/media/ and deployed
    with the code, so they survive Render's ephemeral disk regardless of
    whether the separate Cloudinary backfill has actually finished uploading
    them yet -- SignVideo's Cloudinary storage class computes a
    res.cloudinary.com URL for every row unconditionally, even one that was
    never actually uploaded there, so trusting it blindly would silently
    swap a working local video for a 404. Falls back to that computed URL
    only when no matching local file exists, for anything genuinely
    Cloudinary-only (e.g. a future teacher upload that isn't in the repo).
    """
    lookup = {}
    for video in SignVideo.objects.exclude(video="").only("key", "word", "video"):
        key = _normalize_word_key(video.word)
        if not key or not video.video:
            continue

        relative_name = _resolve_local_relative_name(video)
        if relative_name:
            # Leading "/" is required -- build_absolute_uri() treats a path
            # without one as relative to the current request path (which is
            # /api/games/... here), not root-relative.
            local_path = f"/{settings.MEDIA_URL.strip('/')}/{relative_name}"
            lookup[key] = request.build_absolute_uri(local_path) if request else local_path
            continue

        try:
            url = request.build_absolute_uri(video.video.url) if request else video.video.url
        except Exception:
            continue
        lookup[key] = url
    return lookup


class GameLevelItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameLevelItem
        fields = ["id", "level", "prompt", "answer", "media_url", "extra_data", "order", "created_at", "updated_at"]

    def _sign_video_lookup(self):
        # Views pre-build this once per request and pass it via context
        # (context is shared across every nested item serializer DRF creates
        # for a many=True list), so the SignVideo table is queried once per
        # request instead of once per item. Falls back to building it here
        # for any call site that didn't pass one in.
        if not hasattr(self, "_cached_sign_video_lookup"):
            passed_in = self.context.get("sign_video_lookup")
            self._cached_sign_video_lookup = (
                passed_in if passed_in is not None else build_sign_video_lookup(self.context.get("request"))
            )
        return self._cached_sign_video_lookup

    def _resolve_media_url(self, prompt, stored_url):
        live_url = self._sign_video_lookup().get(_normalize_word_key(prompt))
        return live_url or stored_url

    # media_url/extra_data stay normal writable model fields (instructor CRUD
    # endpoints save them directly) -- only the READ side is patched here, so
    # writes are completely unaffected.
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["media_url"] = self._resolve_media_url(data.get("prompt"), data.get("media_url"))

        extra = data.get("extra_data")
        pool = extra.get("pool") if isinstance(extra, dict) else None
        if isinstance(pool, list) and pool:
            fixed_pool = []
            for entry in pool:
                if isinstance(entry, dict) and entry.get("media_url"):
                    entry = {**entry, "media_url": self._resolve_media_url(entry.get("prompt"), entry.get("media_url"))}
                fixed_pool.append(entry)
            data["extra_data"] = {**extra, "pool": fixed_pool}

        return data


class GameLevelSerializer(serializers.ModelSerializer):
    items = GameLevelItemSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = GameLevel
        fields = [
            "id",
            "game_key",
            "difficulty",
            "level_number",
            "title",
            "is_published",
            "items",
            "items_count",
            "created_at",
            "updated_at",
        ]

    def get_items_count(self, obj):
        return obj.items.count()


class SignVideoSerializer(serializers.ModelSerializer):
    video_url = serializers.SerializerMethodField()

    class Meta:
        model = SignVideo
        fields = ["id", "key", "word", "category", "video_url", "order"]

    def get_video_url(self, obj):
        request = self.context.get("request")
        if obj.video and hasattr(obj.video, "url"):
            if request:
                return request.build_absolute_uri(obj.video.url)
            return obj.video.url
        return None


class AdminSignVideoSerializer(serializers.ModelSerializer):
    video_url = serializers.SerializerMethodField()

    class Meta:
        model = SignVideo
        fields = [
            "id",
            "key",
            "word",
            "category",
            "video_url",
            "order",
            "is_published",
            "text_to_sign_only",
            "created_at",
            "updated_at",
        ]

    def get_video_url(self, obj):
        request = self.context.get("request")
        if obj.video and hasattr(obj.video, "url"):
            if request:
                return request.build_absolute_uri(obj.video.url)
            return obj.video.url
        return None


class StudentQuizQuestionSerializer(serializers.ModelSerializer):
    """Serializer for exposing quiz questions to students (do not include correct answers)."""
    class Meta:
        model = QuizQuestion
        fields = [
            "id",
            "module",
            "question_text",
            "question_type",
            "choices",
            "order",
            "created_at",
            "updated_at",
        ]
