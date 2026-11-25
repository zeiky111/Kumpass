"""Serves /media/ files (sign videos, uploads) with HTTP Range support and caching.

django.views.static.serve always sends the whole file and no Accept-Ranges
header. Safari/iOS won't play a <video> without byte-range responses, and
other browsers re-download the whole file on every loop/seek. With many sign
videos playing and preloading at once on the small backend instance, some of
them timed out. This view answers Range requests with 206 Partial Content and
lets browsers (and the CDN in front of Render) cache videos and images.
"""
import mimetypes
import os
import re

from django.http import FileResponse, Http404, HttpResponse, HttpResponseNotModified
from django.utils._os import safe_join
from django.utils.http import http_date
from django.views.static import was_modified_since

RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")
# Media that never changes in place (a new upload gets a new file name).
CACHEABLE_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v", ".png", ".jpg", ".jpeg", ".gif", ".webp"}
CACHE_SECONDS = 7 * 24 * 3600


def serve_media(request, path, document_root=None):
    try:
        full_path = safe_join(str(document_root), path)
    except Exception:
        raise Http404("Not found")
    if not os.path.isfile(full_path):
        raise Http404("Not found")

    stat = os.stat(full_path)
    if not was_modified_since(request.META.get("HTTP_IF_MODIFIED_SINCE"), int(stat.st_mtime)):
        return HttpResponseNotModified()

    content_type = mimetypes.guess_type(full_path)[0] or "application/octet-stream"
    size = stat.st_size
    match = RANGE_RE.match(request.META.get("HTTP_RANGE", "").strip())

    if match and (match.group(1) or match.group(2)):
        start_text, end_text = match.groups()
        if start_text == "":
            # "bytes=-N": the last N bytes
            start, end = max(0, size - int(end_text)), size - 1
        else:
            start = int(start_text)
            end = int(end_text) if end_text else size - 1
        if start >= size or start > end:
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{size}"
            return response
        end = min(end, size - 1)
        with open(full_path, "rb") as fh:
            fh.seek(start)
            data = fh.read(end - start + 1)
        response = HttpResponse(data, status=206, content_type=content_type)
        response["Content-Range"] = f"bytes {start}-{end}/{size}"
    else:
        response = FileResponse(open(full_path, "rb"), content_type=content_type)
        response["Content-Length"] = str(size)

    response["Accept-Ranges"] = "bytes"
    response["Last-Modified"] = http_date(stat.st_mtime)
    if os.path.splitext(full_path)[1].lower() in CACHEABLE_EXTENSIONS:
        response["Cache-Control"] = f"public, max-age={CACHE_SECONDS}"
    return response
