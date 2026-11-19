"""Download links for module materials and certificates.

Cloudinary accounts block public delivery of PDF/ZIP files by default, so the
plain res.cloudinary.com links for uploaded PDFs answer 401 ("deny or ACL
failure"). Instead, hand out a signed link to our own endpoint, which reads
the file from local disk (pre-Cloudinary uploads) or through Cloudinary's
authenticated download API, and returns it as an attachment.
"""

import io
import logging
import os
import urllib.request

from django.conf import settings
from django.core import signing
from django.http import FileResponse, Http404
from django.urls import reverse

logger = logging.getLogger(__name__)

SALT = "kumpas-file-download"


def download_url(request, kind: str, obj_id: int) -> str:
    """Unguessable link that works without the bearer token (plain <a href>)."""
    token = signing.dumps([kind, obj_id], salt=SALT)
    path = reverse("file-download", args=[token])
    return request.build_absolute_uri(path) if request else path


def read_file_bytes(field) -> bytes:
    name = field.name
    local_path = os.path.join(settings.MEDIA_ROOT, name)
    if os.path.isfile(local_path):
        with open(local_path, "rb") as fh:
            return fh.read()
    if not getattr(settings, "CLOUDINARY_URL", ""):
        raise FileNotFoundError(name)

    import cloudinary.utils

    # Raw uploads keep their extension in the public id, so no format.
    url = cloudinary.utils.private_download_url(name, "", resource_type="raw", type="upload")
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def file_download(request, token: str):
    from .models import ModuleFile, UserCertificate

    try:
        kind, obj_id = signing.loads(token, salt=SALT)
    except signing.BadSignature:
        raise Http404("Invalid link")

    if kind == "module":
        obj = ModuleFile.objects.filter(pk=obj_id).first()
        filename = obj.file_name if obj else ""
    elif kind == "certificate":
        obj = UserCertificate.objects.filter(pk=obj_id).first()
        filename = os.path.basename(obj.file.name) if obj else ""
    else:
        obj = None
    if not obj or not obj.file:
        raise Http404("File not found")

    try:
        data = read_file_bytes(obj.file)
    except Exception:
        logger.exception("Could not fetch %s file %s", kind, obj.file.name)
        raise Http404("File not available")

    return FileResponse(io.BytesIO(data), as_attachment=True, filename=filename or "download")
