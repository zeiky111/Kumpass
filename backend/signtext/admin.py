from django.contrib import admin

from .models import (
    Achievement,
    Announcement,
    Certificate,
    GameLevel,
    GameLevelItem,
    LearningModule,
    Quiz,
    QuizAttempt,
    QuizQuestion,
    QuizQuestionLink,
    SignPredictionLog,
    SignVideo,
    UserAchievement,
    UserCertificate,
    UserProfile,
)


@admin.register(SignPredictionLog)
class SignPredictionLogAdmin(admin.ModelAdmin):
    list_display = ("prediction", "confidence", "source", "created_at")
    search_fields = ("prediction", "source")
    list_filter = ("source", "created_at")


@admin.register(LearningModule)
class LearningModuleAdmin(admin.ModelAdmin):
    list_display = ("module_key", "title", "year_level", "status", "activities_count", "sort_order", "updated_at")
    search_fields = ("module_key", "title", "description")
    list_filter = ("year_level", "status")
    ordering = ("sort_order", "title")


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "module", "question_type", "order", "created_at")
    list_filter = ("question_type",)
    search_fields = ("question_text", "correct_answer")


class QuizQuestionLinkInline(admin.TabularInline):
    model = QuizQuestionLink
    extra = 0
    autocomplete_fields = ("question",)


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "passing_score", "is_published", "updated_at")
    list_filter = ("is_published", "module")
    search_fields = ("title", "module__title")
    inlines = [QuizQuestionLinkInline]


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("title", "game_key", "quiz", "template_path")
    list_filter = ("game_key",)
    search_fields = ("title",)


@admin.register(UserCertificate)
class UserCertificateAdmin(admin.ModelAdmin):
    list_display = ("user", "certificate", "student_name", "issued_at", "emailed")
    search_fields = ("user__username", "student_name", "certificate__title")
    list_filter = ("certificate", "emailed")
    ordering = ("-issued_at",)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "created_at", "updated_at")
    search_fields = ("title", "message")
    list_filter = ("is_published", "created_at")


@admin.register(GameLevel)
class GameLevelAdmin(admin.ModelAdmin):
    list_display = ("game_key", "difficulty", "level_number", "title", "is_published", "updated_at")
    search_fields = ("title",)
    list_filter = ("game_key", "difficulty", "is_published")
    ordering = ("game_key", "difficulty", "level_number")


@admin.register(GameLevelItem)
class GameLevelItemAdmin(admin.ModelAdmin):
    list_display = ("prompt", "level", "answer", "order")
    search_fields = ("prompt", "answer")
    list_filter = ("level__game_key", "level__difficulty")
    ordering = ("level", "order")


@admin.register(SignVideo)
class SignVideoAdmin(admin.ModelAdmin):
    list_display = ("word", "category", "key", "order", "is_published", "updated_at")
    search_fields = ("word", "key")
    list_filter = ("category", "is_published")
    ordering = ("category", "order", "word")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "user", "role", "year_level", "active", "created_at")
    search_fields = ("full_name", "user__email", "role")
    list_filter = ("role", "year_level", "active")


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "module", "quiz", "score", "total", "passed", "created_at")
    search_fields = ("user__username", "module__title")
    list_filter = ("module", "passed", "created_at")
    ordering = ("-created_at",)


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "criteria_type", "criteria_value", "sort_order", "is_active")
    search_fields = ("name", "key")
    list_filter = ("criteria_type", "is_active")
    ordering = ("sort_order", "id")


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ("user", "achievement", "unlocked_at")
    search_fields = ("user__username", "achievement__name")
    list_filter = ("achievement",)
    ordering = ("-unlocked_at",)
