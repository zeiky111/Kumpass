from django.contrib import admin

from .models import Announcement, LearningModule, SignPredictionLog


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


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "created_at", "updated_at")
    search_fields = ("title", "message")
    list_filter = ("is_published", "created_at")
