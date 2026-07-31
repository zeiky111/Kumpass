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
from PIL import Image, ImageDraw, ImageFont

from .models import Certificate, UserCertificate

logger = logging.getLogger(__name__)

REPO_ROOT = settings.BASE_DIR.parent
FONT_PATH = settings.BASE_DIR / "signtext" / "certificate_assets" / "fonts" / "DejaVuSerif-Italic.ttf"

# Measured from the printed underline/name band shared by all 4 templates.
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


def _fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int) -> ImageFont.FreeTypeFont:
    size = MAX_FONT_SIZE
    while size > MIN_FONT_SIZE:
        font = ImageFont.truetype(str(FONT_PATH), size)
        width = draw.textbbox((0, 0), text, font=font)[2]
        if width <= max_width:
            return font
        size -= 2
    return ImageFont.truetype(str(FONT_PATH), MIN_FONT_SIZE)


def _generate_certificate_pdf(template_path: str, student_name: str) -> bytes:
    image_path = REPO_ROOT / template_path
    with Image.open(image_path) as template:
        canvas = template.convert("RGB").copy()

    draw = ImageDraw.Draw(canvas)
    draw.rectangle(
        [(NAME_BAND_LEFT, NAME_BAND_TOP), (NAME_BAND_RIGHT, NAME_BAND_BOTTOM)],
        fill=BACKGROUND_FILL,
    )

    max_width = (NAME_BAND_RIGHT - NAME_BAND_LEFT) - 40
    font = _fit_font(draw, student_name, max_width)
    bbox = draw.textbbox((0, 0), student_name, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = NAME_BAND_LEFT + ((NAME_BAND_RIGHT - NAME_BAND_LEFT) - text_width) / 2 - bbox[0]
    y = NAME_BASELINE_Y - text_height - bbox[1]
    draw.text((x, y), student_name, font=font, fill=INK_COLOR)

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
