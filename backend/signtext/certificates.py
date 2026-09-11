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

from .models import Certificate, LearningModule, UserCertificate

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

# Module completion template (images/modulecert.png) reuses the same
# 1491x1055 canvas and name band as the game templates, plus a second blank
# band below for the issue date line ("issued this Nth day of Month YYYY.").
MODULE_CERT_TEMPLATE_PATH = "images/modulecert.png"
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


def _student_name_for_user(user: User) -> str:
    profile = getattr(user, "profile", None)
    full_name = getattr(profile, "full_name", "") if profile else ""
    return full_name or user.first_name or user.username


def award_certificate_if_earned(user: User, game_key: str) -> UserCertificate | None:
    """Idempotently issues the certificate for game_key to user. Returns the
    newly-created UserCertificate, or None if the game has no certificate
    catalog entry or the user already earned it."""
    try:
        certificate = Certificate.objects.get(game_key=game_key)
    except Certificate.DoesNotExist:
        return None

    if UserCertificate.objects.filter(user=user, certificate=certificate).exists():
        return None

    student_name = _student_name_for_user(user)
    pdf_bytes = _generate_certificate_pdf(certificate.template_path, student_name)

    user_certificate = UserCertificate(user=user, certificate=certificate, student_name=student_name)
    file_name = f"{certificate.game_key}-{user.id}.pdf"
    user_certificate.file.save(file_name, ContentFile(pdf_bytes), save=False)
    user_certificate.save()
    return user_certificate


def award_module_certificate_if_earned(user: User, module: LearningModule) -> UserCertificate | None:
    """Idempotently issues a module-completion certificate to user for the
    given module. Returns the newly-created UserCertificate, or None if the
    user already earned it. Auto-creates the module's Certificate catalog
    entry (all modules share the same modulecert.png template) on first use."""
    certificate, _ = Certificate.objects.get_or_create(
        module=module,
        defaults={
            "title": f"{module.title} — Certificate of Completion",
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
    subject = f"Your {certificate.title} Certificate"
    body = (
        f"Congratulations, {user_certificate.student_name}!\n\n"
        f"You've completed the {certificate.title} on Kumpas. "
        f"Your personalized certificate is attached.\n\n"
        f"Keep up the great work!"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)

    try:
        with user_certificate.file.open("rb") as pdf_file:
            pdf_bytes = pdf_file.read()
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
