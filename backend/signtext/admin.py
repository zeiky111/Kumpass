from django.contrib import admin

from .models import Announcement, GameLevel, GameLevelItem, LearningModule, QuizQuestion, SignPredictionLog, SignVideo, UserProfile


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
