from rest_framework import serializers

from .models import Announcement, LearningModule, ModuleFile, SignPredictionLog, UserLearningState


class SignPredictionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignPredictionLog
        fields = ["id", "prediction", "confidence", "source", "created_at"]


class SignupSerializer(serializers.Serializer):
    fullname = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    role = serializers.CharField(max_length=20, required=False, allow_blank=True)
    yearLevel = serializers.CharField(max_length=20, required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, max_length=128)
    confirmPassword = serializers.CharField(min_length=8, max_length=128)
    securityPin = serializers.CharField(max_length=12, required=False, allow_blank=True)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128)
    role = serializers.CharField(max_length=20)
    securityPin = serializers.CharField(max_length=12, required=False, allow_blank=True)


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
