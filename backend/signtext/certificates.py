"""Certificate PDF generation and issuance.

Each of the 4 game certificate templates (images/2.png .. images/5.png) is a
pre-designed 1491x1055 image with a blank name band centered above a printed
underline. Coordinates below were measured directly from the template pixels
(see the underline at y=551, spanning x=289..1201) so the generated name
lines up with the printed underline on every template.
"""
import io
import logging
import threading
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from .file_downloads import read_file_bytes

from .models import Certificate, LearningModule, QuizAttempt, QuizQuestion, UserCertificate

logger = logging.getLogger(__name__)

REPO_ROOT = settings.BASE_DIR.parent
FONT_PATH = settings.BASE_DIR / "signtext" / "certificate_assets" / "fonts" / "DejaVuSerif-Italic.ttf"

# Measured from the printed underline/name band shared by all 4 game templates.
NAME_BAND_LEFT = 289
NAME_BAND_RIGHT = 1201
NAME_BAND_TOP = 415
NAME_BAND_BOTTOM = 545
UNDERLINE_Y = 551
NAME_BASELINE_Y = UNDERLINE_Y - 14
BACKGROUND_FILL = (246, 246, 246)
INK_COLOR = (26, 57, 135)
MAX_FONT_SIZE = 92
MIN_FONT_SIZE = 36

# Module certificate template reuses the same 1491x1055 canvas and name band
# as the game templates, plus a second blank band below for the issue date
# line ("issued this Nth day of Month YYYY."). modulecert-achievement.png is
# images/modulecert.png with the heading changed to "CERTIFICATE OF
# ACHIEVEMENT"; the certificate is issued when a module's post-test is passed.
MODULE_CERT_TEMPLATE_PATH = "images/modulecert-achievement.png"
MODULE_CERT_TITLE_SUFFIX = "Certificate of Achievement"
DATE_BAND_LEFT = 400
DATE_BAND_RIGHT = 1090
DATE_BAND_TOP = 725
DATE_BAND_BOTTOM = 760
DATE_BASELINE_Y = 756
DATE_BACKGROUND_FILL = (250, 250, 250)
DATE_INK_COLOR = (30, 30, 30)
DATE_MAX_FONT_SIZE = 32
DATE_MIN_FONT_SIZE = 18


def _fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, font_path: Path = FONT_PATH,
              max_size: int = MAX_FONT_SIZE, min_size: int = MIN_FONT_SIZE) -> ImageFont.FreeTypeFont:
    size = max_size
    while size > min_size:
        font = ImageFont.truetype(str(font_path), size)
        width = draw.textbbox((0, 0), text, font=font)[2]
        if width <= max_width:
            return font
        size -= 2
    return ImageFont.truetype(str(font_path), min_size)


def _ordinal(day: int) -> str:
    if 11 <= day % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


def _stamp_centered_text(draw: ImageDraw.ImageDraw, text: str, *, left: int, right: int,
                          baseline_y: int, fill: tuple, font_path: Path, max_size: int, min_size: int) -> None:
    max_width = (right - left) - 40
    font = _fit_font(draw, text, max_width, font_path=font_path, max_size=max_size, min_size=min_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = left + ((right - left) - text_width) / 2 - bbox[0]
    y = baseline_y - text_height - bbox[1]
    draw.text((x, y), text, font=font, fill=fill)


def _generate_certificate_pdf(template_path: str, student_name: str) -> bytes:
    image_path = REPO_ROOT / template_path
    with Image.open(image_path) as template:
        canvas = template.convert("RGB").copy()

    draw = ImageDraw.Draw(canvas)
    draw.rectangle(
        [(NAME_BAND_LEFT, NAME_BAND_TOP), (NAME_BAND_RIGHT, NAME_BAND_BOTTOM)],
        fill=BACKGROUND_FILL,
    )
    _stamp_centered_text(
        draw, student_name,
        left=NAME_BAND_LEFT, right=NAME_BAND_RIGHT, baseline_y=NAME_BASELINE_Y,
        fill=INK_COLOR, font_path=FONT_PATH, max_size=MAX_FONT_SIZE, min_size=MIN_FONT_SIZE,
    )

    buffer = io.BytesIO()
    canvas.save(buffer, format="PDF")
    return buffer.getvalue()


def _generate_module_certificate_pdf(template_path: str, student_name: str, issued_at) -> bytes:
    image_path = REPO_ROOT / template_path
    with Image.open(image_path) as template:
        canvas = template.convert("RGB").copy()

    draw = ImageDraw.Draw(canvas)
    draw.rectangle(
        [(NAME_BAND_LEFT, NAME_BAND_TOP), (NAME_BAND_RIGHT, NAME_BAND_BOTTOM)],
        fill=BACKGROUND_FILL,
    )
    _stamp_centered_text(
        draw, student_name,
        left=NAME_BAND_LEFT, right=NAME_BAND_RIGHT, baseline_y=NAME_BASELINE_Y,
        fill=INK_COLOR, font_path=FONT_PATH, max_size=MAX_FONT_SIZE, min_size=MIN_FONT_SIZE,
    )

    draw.rectangle(
        [(DATE_BAND_LEFT, DATE_BAND_TOP), (DATE_BAND_RIGHT, DATE_BAND_BOTTOM)],
        fill=DATE_BACKGROUND_FILL,
    )
    date_text = f"issued this {_ordinal(issued_at.day)} day of {issued_at.strftime('%B %Y')}."
    _stamp_centered_text(
        draw, date_text,
        left=DATE_BAND_LEFT, right=DATE_BAND_RIGHT, baseline_y=DATE_BASELINE_Y,
        fill=DATE_INK_COLOR, font_path=FONT_PATH, max_size=DATE_MAX_FONT_SIZE, min_size=DATE_MIN_FONT_SIZE,
    )

    buffer = io.BytesIO()
    canvas.save(buffer, format="PDF")
    return buffer.getvalue()


# ---- Certificate templates (Canva designs, 1491x1055) ----
# Games: "Certificate of Achievement", one template per game.
# Learning modules: one "Certificate of Completion" once EVERY module is passed.
# The templates have a blank name band, a blank date line and a blank
# certificate number; the system stamps all three when issuing.
FONTS_DIR = settings.BASE_DIR / "signtext" / "certificate_assets" / "fonts"
NAME_FONT_PATH = FONTS_DIR / "GreatVibes-Regular.ttf"      # script, like the design's sample name
TEXT_FONT_PATH = FONTS_DIR / "Poppins-Regular.ttf"          # date line
NUMBER_FONT_PATH = FONTS_DIR / "Poppins-Medium.ttf"         # certificate number

GAME_CERT_TEMPLATES = {
    "sign_match": ("images/cert-game-sign-match.png", "Sign Match Game — Certificate of Achievement"),
    "typing": ("images/cert-game-typing.png", "Sign-to-Word Game — Certificate of Achievement"),
    "sentence": ("images/cert-game-sentence.png", "Sentence Builder Game — Certificate of Achievement"),
    "scenario": ("images/cert-game-scenario.png", "Scenario-Based Game — Certificate of Achievement"),
}
MODULES_CERT_TEMPLATE_PATH = "images/cert-modules-completion.png"

# Positions measured on the templates.
NEW_NAME_LEFT, NEW_NAME_RIGHT = 300, 1190
NEW_NAME_BASELINE = 528          # just above the printed underline (y=551)
NEW_NAME_COLOR = (25, 56, 132)
NEW_NAME_MAX, NEW_NAME_MIN = 118, 56
NEW_DATE_CENTER_X, NEW_DATE_BASELINE = 745, 752
NEW_DATE_COLOR = (20, 20, 20)
NEW_DATE_SIZE = 25
NEW_NUMBER_CENTER_X, NEW_NUMBER_BASELINE = 1190, 901
NEW_NUMBER_COLOR = (22, 43, 99)
NEW_NUMBER_SIZE = 16


def _text_width(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font, anchor="ls")
    return box[2] - box[0]


def _render_certificate_pdf(template_path: str, student_name: str, issued_at, certificate_number: str) -> bytes:
    """Stamps the student's name, the issue date and the certificate number
    onto one of the new templates and returns the PDF bytes."""
    with Image.open(REPO_ROOT / template_path) as template:
        canvas = template.convert("RGB").copy()
    draw = ImageDraw.Draw(canvas)

    # Name: script font, as large as fits the name band.
    size = NEW_NAME_MAX
    while size > NEW_NAME_MIN:
        name_font = ImageFont.truetype(str(NAME_FONT_PATH), size)
        if _text_width(draw, student_name, name_font) <= NEW_NAME_RIGHT - NEW_NAME_LEFT:
            break
        size -= 2
    name_font = ImageFont.truetype(str(NAME_FONT_PATH), size)
    center = (NEW_NAME_LEFT + NEW_NAME_RIGHT) / 2
    draw.text((center, NEW_NAME_BASELINE), student_name, font=name_font, fill=NEW_NAME_COLOR, anchor="ms")

    # Date: "issued this 27th day of July 2026." with a raised ordinal suffix.
    day = issued_at.day
    suffix = "th" if 11 <= day % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    date_font = ImageFont.truetype(str(TEXT_FONT_PATH), NEW_DATE_SIZE)
    sup_font = ImageFont.truetype(str(TEXT_FONT_PATH), int(NEW_DATE_SIZE * 0.6))
    before = f"issued this {day}"
    after = f" day of {issued_at.strftime('%B %Y')}."
    total = _text_width(draw, before, date_font) + _text_width(draw, suffix, sup_font) + _text_width(draw, after, date_font)
    x = NEW_DATE_CENTER_X - total / 2
    draw.text((x, NEW_DATE_BASELINE), before, font=date_font, fill=NEW_DATE_COLOR, anchor="ls")
    x += _text_width(draw, before, date_font)
    draw.text((x, NEW_DATE_BASELINE - int(NEW_DATE_SIZE * 0.42)), suffix, font=sup_font, fill=NEW_DATE_COLOR, anchor="ls")
    x += _text_width(draw, suffix, sup_font)
    draw.text((x, NEW_DATE_BASELINE), after, font=date_font, fill=NEW_DATE_COLOR, anchor="ls")

    # Certificate number, on the "CERTIFICATE NO." line.
    number_font = ImageFont.truetype(str(NUMBER_FONT_PATH), NEW_NUMBER_SIZE)
    draw.text((NEW_NUMBER_CENTER_X, NEW_NUMBER_BASELINE), certificate_number, font=number_font,
              fill=NEW_NUMBER_COLOR, anchor="ms")

    buffer = io.BytesIO()
    canvas.save(buffer, format="PDF", resolution=150)
    return buffer.getvalue()


def _next_certificate_number(issued_at) -> str:
    """KMP-<year>-<MMDD>-<running number for that day>, e.g. KMP-2026-0727-0001."""
    prefix = f"KMP-{issued_at:%Y}-{issued_at:%m%d}-"
    last = (
        UserCertificate.objects.filter(certificate_number__startswith=prefix)
        .order_by("-certificate_number")
        .values_list("certificate_number", flat=True)
        .first()
    )
    try:
        sequence = int(str(last).rsplit("-", 1)[1]) + 1 if last else 1
    except (IndexError, ValueError):
        sequence = UserCertificate.objects.filter(certificate_number__startswith=prefix).count() + 1
    return f"{prefix}{sequence:04d}"


def _issue_certificate(user: User, certificate: Certificate, file_stem: str) -> UserCertificate:
    """Creates the UserCertificate with a unique number and its PDF."""
    from django.db import IntegrityError, transaction

    student_name = _student_name_for_user(user)
    issued_at = timezone.localtime(timezone.now())
    for _attempt in range(5):
        number = _next_certificate_number(issued_at)
        pdf_bytes = _render_certificate_pdf(certificate.template_path, student_name, issued_at, number)
        user_certificate = UserCertificate(
            user=user, certificate=certificate, student_name=student_name, certificate_number=number
        )
        try:
            with transaction.atomic():
                user_certificate.file.save(f"{file_stem}-{number}.pdf", ContentFile(pdf_bytes), save=False)
                user_certificate.save()
            return user_certificate
        except IntegrityError:
            # Another certificate took this number at the same moment; take the next one.
            if UserCertificate.objects.filter(user=user, certificate=certificate).exists():
                return UserCertificate.objects.get(user=user, certificate=certificate)
            continue
    raise RuntimeError("Could not allocate a certificate number")


def verify_certificate_number(number: str):
    """Returns the issued certificate for a number, or None."""
    number = str(number or "").strip().upper()
    if not number:
        return None
    return UserCertificate.objects.select_related("certificate").filter(certificate_number=number).first()


def _student_name_for_user(user: User) -> str:
    profile = getattr(user, "profile", None)
    full_name = getattr(profile, "full_name", "") if profile else ""
    return full_name or user.first_name or user.username


def award_certificate_if_earned(user: User, game_key: str) -> UserCertificate | None:
    """Idempotently issues the game's Certificate of Achievement (called once
    the game's Hard difficulty is passed). Returns the new UserCertificate, or
    None for an unknown game or one the user already earned."""
    if game_key not in GAME_CERT_TEMPLATES:
        return None
    template_path, title = GAME_CERT_TEMPLATES[game_key]
    certificate, _ = Certificate.objects.get_or_create(
        game_key=game_key, defaults={"title": title, "template_path": template_path}
    )
    if certificate.template_path != template_path or certificate.title != title:
        certificate.template_path, certificate.title = template_path, title
        certificate.save(update_fields=["template_path", "title"])

    if UserCertificate.objects.filter(user=user, certificate=certificate).exists():
        return None
    return _issue_certificate(user, certificate, f"{game_key}-{user.id}")


def award_module_certificate_if_earned(user: User, module: LearningModule) -> UserCertificate | None:
    """Idempotently issues a module Certificate of Achievement to user for the
    given module. Returns the newly-created UserCertificate, or None if the
    user already earned it. Auto-creates the module's Certificate catalog
    entry (all modules share the same modulecert.png template) on first use."""
    certificate, _ = Certificate.objects.get_or_create(
        module=module,
        defaults={
            "title": f"{module.title} — {MODULE_CERT_TITLE_SUFFIX}",
            "template_path": MODULE_CERT_TEMPLATE_PATH,
        },
    )

    if UserCertificate.objects.filter(user=user, certificate=certificate).exists():
        return None

    student_name = _student_name_for_user(user)
    issued_at = timezone.now()
    pdf_bytes = _generate_module_certificate_pdf(certificate.template_path, student_name, issued_at)

    user_certificate = UserCertificate(user=user, certificate=certificate, student_name=student_name)
    file_name = f"module-{module.module_key}-{user.id}.pdf"
    user_certificate.file.save(file_name, ContentFile(pdf_bytes), save=False)
    user_certificate.save()
    return user_certificate


# The modules certificate ("Certificate of Completion"): issued once a student
# has completed and passed EVERY published learning module. Passing a single
# module earns an achievement instead (see views._unlock_module_achievement).
ALL_MODULES_CERT_TITLE = "Kumpas Learning Modules — Certificate of Completion"
ALL_MODULES_PASSING_PERCENT = 75


def _all_modules_certificate() -> Certificate:
    # The old all-modules certificate (no game, no module, no level).
    certificate = Certificate.objects.filter(game_key__isnull=True, module__isnull=True, level__isnull=True).first()
    if certificate is None:
        certificate = Certificate.objects.create(title=ALL_MODULES_CERT_TITLE, template_path=MODULES_CERT_TEMPLATE_PATH)
    elif certificate.title != ALL_MODULES_CERT_TITLE or certificate.template_path != MODULES_CERT_TEMPLATE_PATH:
        certificate.title, certificate.template_path = ALL_MODULES_CERT_TITLE, MODULES_CERT_TEMPLATE_PATH
        certificate.save(update_fields=["title", "template_path"])
    return certificate


def unpassed_module_count(user: User) -> int:
    """Published modules whose post-test this user hasn't passed (75%+) yet."""
    module_ids = list(
        LearningModule.objects.filter(status=LearningModule.STATUS_PUBLISHED).values_list("id", flat=True)
    )
    passed = {
        attempt.module_id
        for attempt in QuizAttempt.objects.filter(
            user=user, test_type=QuizQuestion.TEST_POST, module_id__in=module_ids
        ).only("module_id", "score", "total")
        if attempt.total and attempt.score / attempt.total * 100 >= ALL_MODULES_PASSING_PERCENT
    }
    return len([module_id for module_id in module_ids if module_id not in passed])


def award_all_modules_certificate_if_earned(user: User) -> UserCertificate | None:
    """Issues the Kumpas certificate once every published module is passed.
    Idempotent: returns None if not earned yet or already issued."""
    if not LearningModule.objects.filter(status=LearningModule.STATUS_PUBLISHED).exists():
        return None
    if unpassed_module_count(user) > 0:
        return None

    certificate = _all_modules_certificate()
    if UserCertificate.objects.filter(user=user, certificate=certificate).exists():
        return None

    return _issue_certificate(user, certificate, f"kumpas-modules-{user.id}")


def _send_certificate_email_sync(user_certificate_id: int) -> None:
    try:
        user_certificate = UserCertificate.objects.select_related("user", "certificate").get(
            id=user_certificate_id
        )
    except UserCertificate.DoesNotExist:
        return

    user = user_certificate.user
    recipient = (user.email or "").strip()
    if not recipient:
        logger.warning("Cannot email certificate %s: user %s has no email", user_certificate_id, user.username)
        return

    certificate = user_certificate.certificate
    # Titles already say "Certificate of ..."; don't add a second "Certificate".
    subject = f"Your {certificate.title}" if "certificate" in certificate.title.lower() else f"Your {certificate.title} Certificate"
    body = (
        f"Congratulations, {user_certificate.student_name}!\n\n"
        f"You've completed the {certificate.title} on Kumpas. "
        f"Your personalized certificate is attached.\n\n"
        f"Keep up the great work!"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)

    try:
        pdf_bytes = read_file_bytes(user_certificate.file)
        message = EmailMessage(subject, body, from_email, [recipient])
        message.attach(f"{certificate.title}.pdf", pdf_bytes, "application/pdf")
        message.send(fail_silently=False)
        UserCertificate.objects.filter(id=user_certificate_id).update(emailed=True)
        logger.info("Certificate email sent to %s for %s", recipient, certificate.game_key)
    except Exception:
        logger.exception("Failed to email certificate %s to %s", user_certificate_id, recipient)


def send_certificate_email_async(user_certificate: UserCertificate) -> None:
    thread = threading.Thread(
        target=_send_certificate_email_sync,
        args=(user_certificate.id,),
        daemon=True,
    )
    thread.start()


def upgrade_legacy_certificates(user: User) -> int:
    """Re-issues this user's game / all-modules certificates that were made
    before certificate numbers existed (old design, no number): same
    certificate, now on the new template with a system-generated number.
    Returns how many were upgraded. Safe to call repeatedly."""
    upgraded = 0
    legacy = UserCertificate.objects.filter(user=user, certificate_number__isnull=True).select_related("certificate")
    for user_certificate in legacy:
        certificate = user_certificate.certificate
        if certificate.module_id is not None:
            continue  # old per-module certificates are now achievements
        if certificate.game_key:
            if certificate.game_key not in GAME_CERT_TEMPLATES:
                continue
            template_path, title = GAME_CERT_TEMPLATES[certificate.game_key]
            if certificate.template_path != template_path or certificate.title != title:
                certificate.template_path, certificate.title = template_path, title
                certificate.save(update_fields=["template_path", "title"])
            stem = f"{certificate.game_key}-{user.id}"
        else:
            certificate = _all_modules_certificate()
            stem = f"kumpas-modules-{user.id}"
        try:
            issued_at = timezone.localtime(user_certificate.issued_at)
            number = _next_certificate_number(timezone.localtime(timezone.now()))
            pdf_bytes = _render_certificate_pdf(certificate.template_path, user_certificate.student_name, issued_at, number)
            user_certificate.certificate_number = number
            user_certificate.file.save(f"{stem}-{number}.pdf", ContentFile(pdf_bytes), save=False)
            user_certificate.save(update_fields=["certificate_number", "file"])
            upgraded += 1
        except Exception:
            logger.exception("Could not upgrade legacy certificate %s", user_certificate.id)
    return upgraded


# ---- Certificate of Completion per level ----
# A student earns a level's certificate once they have passed (75%+) the
# post-test of every published module in that level. Passing a single module
# earns an achievement; finishing a game (Hard) earns that game's certificate.
LEVEL_CERT_TEMPLATES = {
    "beginner": ("images/cert-level-beginner.png", "Beginner Level — Certificate of Completion", "Beginner"),
    "intermediate": ("images/cert-level-intermediate.png", "Intermediate Level — Certificate of Completion", "Intermediate"),
    "advanced": ("images/cert-level-advanced.png", "Advanced Level — Certificate of Completion", "Advanced"),
}


def _level_certificate(level: str) -> Certificate:
    template_path, title, _label = LEVEL_CERT_TEMPLATES[level]
    certificate, _ = Certificate.objects.get_or_create(
        level=level, defaults={"title": title, "template_path": template_path}
    )
    if certificate.title != title or certificate.template_path != template_path:
        certificate.title, certificate.template_path = title, template_path
        certificate.save(update_fields=["title", "template_path"])
    return certificate


def level_progress(user: User) -> dict:
    """{level: {"total": published modules, "passed": modules passed}} for every level."""
    from .views import _normalize_module_level  # local import: views imports this module

    progress = {level: {"total": 0, "passed": 0} for level in LEVEL_CERT_TEMPLATES}
    published = list(
        LearningModule.objects.filter(status=LearningModule.STATUS_PUBLISHED).values_list("id", "year_level")
    )
    passed_ids = {
        attempt.module_id
        for attempt in QuizAttempt.objects.filter(
            user=user, test_type=QuizQuestion.TEST_POST, module_id__in=[mid for mid, _ in published]
        ).only("module_id", "score", "total")
        if attempt.total and attempt.score / attempt.total * 100 >= ALL_MODULES_PASSING_PERCENT
    }
    for module_id, year_level in published:
        level = _normalize_module_level(year_level)
        if level not in progress:
            continue
        progress[level]["total"] += 1
        if module_id in passed_ids:
            progress[level]["passed"] += 1
    return progress


def award_level_certificates_if_earned(user: User) -> list:
    """Issues each level's certificate the student has earned but not received
    yet. Returns the newly issued UserCertificates (usually none or one)."""
    issued = []
    for level, counts in level_progress(user).items():
        if counts["total"] == 0 or counts["passed"] < counts["total"]:
            continue
        certificate = _level_certificate(level)
        if UserCertificate.objects.filter(user=user, certificate=certificate).exists():
            continue
        issued.append(_issue_certificate(user, certificate, f"kumpas-{level}-{user.id}"))
    return issued
