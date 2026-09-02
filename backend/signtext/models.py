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
    student_id = models.CharField(max_length=40, blank=True, default="")
    contact_number = models.CharField(max_length=30, blank=True, default="")
    hearing_status = models.CharField(max_length=30, blank=True, default="")
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
    # FSL-105 dataset categories (backend/datasets/fsl105/labels.csv)
    CATEGORY_CALENDAR = "calendar"
    CATEGORY_COLORS = "colors"
    CATEGORY_NUMBERS = "numbers"
    CATEGORY_DAYS = "days"
    CATEGORY_FAMILY = "family"
    CATEGORY_RELATIONSHIPS = "relationships"
    CATEGORY_FOOD = "food"
    CATEGORY_DRINK = "drink"
    CATEGORY_SURVIVAL = "survival"
    CATEGORY_CHOICES = [
        (CATEGORY_ALPHABET, "Alphabet"),
        (CATEGORY_EMOTIONS, "Emotions"),
        (CATEGORY_EVERYDAY_WORDS, "Everyday Words"),
        (CATEGORY_EXPRESSIONS, "Expressions"),
        (CATEGORY_GREETINGS, "Greetings"),
        (CATEGORY_PHRASES, "Phrases"),
        (CATEGORY_RESPONSES, "Responses"),
        (CATEGORY_CALENDAR, "Calendar"),
        (CATEGORY_COLORS, "Colors"),
        (CATEGORY_NUMBERS, "Numbers"),
        (CATEGORY_DAYS, "Days"),
        (CATEGORY_FAMILY, "Family"),
        (CATEGORY_RELATIONSHIPS, "Relationships"),
        (CATEGORY_FOOD, "Food"),
        (CATEGORY_DRINK, "Drink"),
        (CATEGORY_SURVIVAL, "Survival"),
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


class QuizAttempt(models.Model):
    """Records one graded quiz submission for a module, used to compute
    per-module accuracy (skill breakdown) and quiz-based achievements."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quiz_attempts")
    module = models.ForeignKey(LearningModule, on_delete=models.CASCADE, related_name="quiz_attempts")
    score = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user.username} - {self.module.module_key} ({self.score}/{self.total})"


class Achievement(models.Model):
    """Achievement catalog entry. Unlock criteria are data-driven (criteria_type
    + criteria_value) so new achievements can be added without code changes."""
    CRITERIA_MODULES_COMPLETED = "modules_completed"
    CRITERIA_STREAK_DAYS = "streak_days"
    CRITERIA_QUIZ_PERFECT_SCORE = "quiz_perfect_score"
    CRITERIA_QUIZ_COUNT = "quiz_count"
    CRITERIA_POINTS_TOTAL = "points_total"
    CRITERIA_CHOICES = [
        (CRITERIA_MODULES_COMPLETED, "Modules completed"),
        (CRITERIA_STREAK_DAYS, "Streak (days)"),
        (CRITERIA_QUIZ_PERFECT_SCORE, "Perfect quiz scores"),
        (CRITERIA_QUIZ_COUNT, "Quizzes taken"),
        (CRITERIA_POINTS_TOTAL, "Points total"),
    ]

    key = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    icon = models.CharField(max_length=60, default="fa-solid fa-award")
    criteria_type = models.CharField(max_length=30, choices=CRITERIA_CHOICES)
    criteria_value = models.PositiveIntegerField(default=1)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.name


class UserAchievement(models.Model):
    """Records that a user has unlocked a given achievement."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="unlocked_achievements")
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name="unlocks")
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "achievement")
        ordering = ["-unlocked_at"]

    def __str__(self) -> str:
        return f"{self.user.username} unlocked {self.achievement.key}"


class Certificate(models.Model):
    """Certificate catalog entry: one row per game, defining its template."""
    game_key = models.CharField(max_length=20, choices=GameLevel.GAME_CHOICES, unique=True)
    title = models.CharField(max_length=150)
    template_path = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.title


class UserCertificate(models.Model):
    """Records that a user earned a given game's certificate and stores the
    generated PDF, personalized with the student's name at issue time."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="certificates")
    certificate = models.ForeignKey(Certificate, on_delete=models.CASCADE, related_name="unlocks")
    file = models.FileField(upload_to="certificates/%Y/%m/")
    student_name = models.CharField(max_length=150)
    issued_at = models.DateTimeField(auto_now_add=True)
    emailed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "certificate")
        ordering = ["-issued_at"]

    def __str__(self) -> str:
        return f"{self.user.username} earned {self.certificate.game_key}"


class FSL105Clip(models.Model):
    """One video clip from the FSL-105 dataset (Mendeley 48y2y99mb9):
    105 Filipino Sign Language classes, 2,130 clips, split train/test.
    Source: https://data.mendeley.com/datasets/48y2y99mb9/2
    """
    SPLIT_TRAIN = "train"
    SPLIT_TEST = "test"
    SPLIT_CHOICES = [
        (SPLIT_TRAIN, "Train"),
        (SPLIT_TEST, "Test"),
    ]

    clip_id = models.PositiveIntegerField(unique=True)
    label = models.CharField(max_length=150, db_index=True)
    category = models.CharField(max_length=150, blank=True, default="")
    split = models.CharField(max_length=10, choices=SPLIT_CHOICES)
    source_path = models.CharField(max_length=500)
    # Raw video bytes stored directly in the row (not a file-storage path),
    # per requirement: the dataset must live inside the database itself.
    video_data = models.BinaryField(null=True, blank=True, editable=True)
    video_filename = models.CharField(max_length=255, blank=True, default="")
    video_content_type = models.CharField(max_length=100, blank=True, default="video/quicktime")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["label", "clip_id"]

    def __str__(self) -> str:
        return f"{self.label} #{self.clip_id} ({self.split})"
