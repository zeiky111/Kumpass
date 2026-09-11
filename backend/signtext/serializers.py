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


class GameLevelItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameLevelItem
        fields = ["id", "level", "prompt", "answer", "media_url", "extra_data", "order", "created_at", "updated_at"]


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
