from django.db import models
from django.contrib.auth.models import User


class SignPredictionLog(models.Model):
    prediction = models.CharField(max_length=64)
    confidence = models.DecimalField(max_digits=5, decimal_places=2)
    source = models.CharField(max_length=32, default="camera")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.prediction} ({self.confidence}%)"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=120)
    year_level = models.CharField(max_length=20, blank=True, default="")
    role = models.CharField(max_length=20, default="student")
    security_pin = models.CharField(max_length=12, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.full_name} ({self.role})"


class UserLearningState(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="learning_state")
    state = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Learning state for {self.user.username}"


class LearningModule(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_ARCHIVED = "archived"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    module_key = models.CharField(max_length=64, unique=True)
    title = models.CharField(max_length=180)
    year_level = models.CharField(max_length=20, default="1")
    description = models.TextField(blank=True, default="")
    activities_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    sort_order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_learning_modules",
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_learning_modules",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "title"]

    def __str__(self) -> str:
        return f"{self.title} ({self.module_key})"


class ModuleFile(models.Model):
    """File attachments for learning modules (docs, ppts, etc.)"""
    FILE_TYPE_CHOICES = [
        ("document", "Document (PDF, Word, etc.)"),
        ("presentation", "Presentation (PPT, etc.)"),
        ("video", "Video"),
        ("image", "Image"),
        ("audio", "Audio"),
        ("other", "Other"),
    ]

    module = models.ForeignKey(
        LearningModule,
        on_delete=models.CASCADE,
        related_name="files",
    )
    file_name = models.CharField(max_length=255)
    file = models.FileField(upload_to="module_files/%Y/%m/%d/")
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, default="document")
    file_size = models.PositiveIntegerField(default=0)  # in bytes
    description = models.CharField(max_length=255, blank=True, default="")
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_module_files",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Module File"
        verbose_name_plural = "Module Files"

    def __str__(self) -> str:
        return f"{self.file_name} (in {self.module.title})"


class Announcement(models.Model):
    title = models.CharField(max_length=180)
    message = models.TextField()
    is_published = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_announcements",
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_announcements",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title
