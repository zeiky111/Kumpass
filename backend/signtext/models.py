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
    first_name = models.CharField(max_length=64, blank=True, default="")
    middle_name = models.CharField(max_length=64, blank=True, default="")
    last_name = models.CharField(max_length=64, blank=True, default="")
    suffix = models.CharField(max_length=32, blank=True, default="")
    year_level = models.CharField(max_length=20, blank=True, default="")
    role = models.CharField(max_length=20, default="student")
    security_pin = models.CharField(max_length=12, blank=True, default="")
    # 0 = active, 1 = inactive (admin can toggle to deactivate instructors)
    active = models.IntegerField(default=0)
    photo = models.ImageField(upload_to="profile_photos/%Y/%m/%d/", blank=True, null=True)
    # Preset mascot avatar id (e.g. "blue", "purple"); mutually exclusive with photo.
    avatar_id = models.CharField(max_length=32, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if any([self.first_name, self.middle_name, self.last_name, self.suffix]):
            parts = [self.first_name, self.middle_name, self.last_name, self.suffix]
            self.full_name = " ".join([part for part in parts if part]).strip()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.full_name} ({self.role})"


class UserLearningState(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="learning_state")
    state = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Learning state for {self.user.username}"


class EmailOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_otps")
    otp = models.CharField(max_length=8)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"OTP for {self.user.username} (expires {self.expires_at.isoformat()})"


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


class QuizQuestion(models.Model):
    QUESTION_TYPE_MULTIPLE_CHOICE = "multiple_choice"
    QUESTION_TYPE_IDENTIFICATION = "identification"
    QUESTION_TYPE_CHOICES = [
        (QUESTION_TYPE_MULTIPLE_CHOICE, "Multiple Choice"),
        (QUESTION_TYPE_IDENTIFICATION, "Identification"),
    ]

    module = models.ForeignKey(
        LearningModule,
        on_delete=models.CASCADE,
        related_name="quiz_questions",
    )
    question_text = models.TextField()
    question_type = models.CharField(
        max_length=30,
        choices=QUESTION_TYPE_CHOICES,
        default=QUESTION_TYPE_MULTIPLE_CHOICE,
    )
    choices = models.JSONField(default=list, blank=True)
    correct_answer = models.CharField(max_length=255, blank=True, default="")
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self) -> str:
        return f"{self.question_text[:50]}... ({self.module.title})"


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


class GameLevel(models.Model):
    GAME_SIGN_MATCH = "sign_match"
    GAME_TYPING = "typing"
    GAME_SENTENCE = "sentence"
    GAME_SCENARIO = "scenario"
    GAME_CHOICES = [
        (GAME_SIGN_MATCH, "Sign Match Game"),
        (GAME_TYPING, "Sign-to-Word Typing Game"),
        (GAME_SENTENCE, "Sentence Builder Game"),
        (GAME_SCENARIO, "Scenario-Based Game"),
    ]

    DIFFICULTY_EASY = "easy"
    DIFFICULTY_MEDIUM = "medium"
    DIFFICULTY_HARD = "hard"
    DIFFICULTY_CHOICES = [
        (DIFFICULTY_EASY, "Easy"),
        (DIFFICULTY_MEDIUM, "Medium"),
        (DIFFICULTY_HARD, "Hard"),
    ]

    game_key = models.CharField(max_length=20, choices=GAME_CHOICES)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default=DIFFICULTY_EASY)
    level_number = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=150, blank=True, default="")
    is_published = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_game_levels",
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_game_levels",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["game_key", "difficulty", "level_number"]
        unique_together = ("game_key", "difficulty", "level_number")

    def __str__(self) -> str:
        return f"{self.get_game_key_display()} - {self.get_difficulty_display()} - Level {self.level_number}"


class SignVideo(models.Model):
    """Sign language demonstration video, sourced from the Sign Language media library.

    Serves as the shared data source for both the Games and the Text-to-Sign
    modules so both features read from the same set of videos.
    """
    CATEGORY_ALPHABET = "alphabet"
    CATEGORY_EMOTIONS = "emotions"
    CATEGORY_EVERYDAY_WORDS = "everyday_words"
    CATEGORY_EXPRESSIONS = "expressions"
    CATEGORY_GREETINGS = "greetings"
    CATEGORY_PHRASES = "phrases"
    CATEGORY_RESPONSES = "responses"
    CATEGORY_CHOICES = [
        (CATEGORY_ALPHABET, "Alphabet"),
        (CATEGORY_EMOTIONS, "Emotions"),
        (CATEGORY_EVERYDAY_WORDS, "Everyday Words"),
        (CATEGORY_EXPRESSIONS, "Expressions"),
        (CATEGORY_GREETINGS, "Greetings"),
        (CATEGORY_PHRASES, "Phrases"),
        (CATEGORY_RESPONSES, "Responses"),
    ]

    key = models.CharField(max_length=120, unique=True, db_index=True)
    word = models.CharField(max_length=150)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default=CATEGORY_PHRASES)
    video = models.FileField(upload_to="sign_videos/%Y/%m/%d/")
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    # True for videos uploaded via the Admin "Sign Language Videos" manager --
    # keeps them out of the Games' shared /sign-videos/?scope=games query so
    # admin uploads only power Text-to-Sign, not the Games.
    text_to_sign_only = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "order", "word"]

    def __str__(self) -> str:
        return f"{self.word} ({self.get_category_display()})"


class GameLevelItem(models.Model):
    level = models.ForeignKey(
        GameLevel,
        on_delete=models.CASCADE,
        related_name="items",
    )
    prompt = models.CharField(max_length=255)
    answer = models.CharField(max_length=255, blank=True, default="")
    media_url = models.CharField(max_length=500, blank=True, default="")
    extra_data = models.JSONField(default=dict, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return f"{self.prompt} (level {self.level_id})"
