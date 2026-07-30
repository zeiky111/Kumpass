from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from signtext.models import SignVideo

# Maps each "Sign Language/<Category>/<file>" folder to a SignVideo category
# code, plus an explicit filename -> display word mapping. An explicit map
# (rather than a generic underscore-to-space transform) keeps labels like
# "I'm fine" and "You're welcome" correct instead of "Im fine" / "You re welcome".
CATEGORY_FOLDERS = {
    "Alphabets": SignVideo.CATEGORY_ALPHABET,
    "Emotions": SignVideo.CATEGORY_EMOTIONS,
    "Everyday Words": SignVideo.CATEGORY_EVERYDAY_WORDS,
    "Expressions": SignVideo.CATEGORY_EXPRESSIONS,
    "Greetings": SignVideo.CATEGORY_GREETINGS,
    "Phrases": SignVideo.CATEGORY_PHRASES,
    "Responses": SignVideo.CATEGORY_RESPONSES,
}

WORD_OVERRIDES = {
    "Excuse_me": "Excuse me",
    "Thank_you": "Thank you",
    "You_re_welcome": "You're welcome",
    "Good_afternoon": "Good afternoon",
    "Good_evening": "Good evening",
    "Good_morning": "Good morning",
    "Can_you_repeat_that": "Can you repeat that",
    "How_are_you": "How are you",
    "Im_fine": "I'm fine",
    "I_need_help": "I need help",
    "My_name_is": "My name is",
    "Nice_to_meet_you": "Nice to meet you",
    "What_is_your_name": "What is your name",
    "I_dont_understand": "I don't understand",
    "I_understand": "I understand",
}

VIDEO_EXTENSIONS = {".mov", ".mp4", ".webm", ".m4v"}


def _label_for_stem(stem: str) -> str:
    if stem in WORD_OVERRIDES:
        return WORD_OVERRIDES[stem]
    return stem.replace("_", " ").strip()


def _key_for_label(label: str) -> str:
    return label.strip().lower()


class Command(BaseCommand):
    help = "Import sign language videos from the 'Sign Language' folder into the SignVideo table."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default=None,
            help="Path to the Sign Language folder (default: <project root>/Sign Language).",
        )
        parser.add_argument(
            "--no-clear",
            action="store_true",
            help="Do not delete existing SignVideo rows before importing.",
        )

    def handle(self, *args, **options):
        source_arg = options.get("source")
        if source_arg:
            source_dir = Path(source_arg)
        else:
            # BASE_DIR (backend/) parent is the project root where "Sign Language" lives.
            from django.conf import settings

            source_dir = Path(settings.BASE_DIR).parent / "Sign Language"

        if not source_dir.is_dir():
            raise CommandError(f"Source folder not found: {source_dir}")

        if not options.get("no_clear"):
            existing = SignVideo.objects.all()
            count = existing.count()
            for video in existing:
                if video.video:
                    video.video.delete(save=False)
            existing.delete()
            self.stdout.write(f"Cleared {count} existing SignVideo record(s).")

        imported = 0
        skipped = []

        for folder_name, category in CATEGORY_FOLDERS.items():
            folder_path = source_dir / folder_name
            if not folder_path.is_dir():
                self.stdout.write(self.style.WARNING(f"Skipping missing folder: {folder_path}"))
                continue

            order = 0
            for file_path in sorted(folder_path.iterdir()):
                if not file_path.is_file() or file_path.suffix.lower() not in VIDEO_EXTENSIONS:
                    continue

                label = _label_for_stem(file_path.stem)
                key = _key_for_label(label)
                order += 1

                with file_path.open("rb") as fh:
                    django_file = File(fh, name=file_path.name)
                    video, _created = SignVideo.objects.update_or_create(
                        key=key,
                        defaults={
                            "word": label,
                            "category": category,
                            "order": order,
                        },
                    )
                    video.video.save(file_path.name, django_file, save=True)

                imported += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {imported} sign video(s) from {source_dir}."))
        if skipped:
            self.stdout.write(self.style.WARNING(f"Skipped: {', '.join(skipped)}"))
