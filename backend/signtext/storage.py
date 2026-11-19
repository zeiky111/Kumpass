import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from cloudinary_storage.storage import RawMediaCloudinaryStorage, VideoMediaCloudinaryStorage


class LocalFirstMixin:
    """Serve files that already exist under MEDIA_ROOT from /media/.

    Files uploaded before Cloudinary was enabled live in backend/media (they
    ship with the repo and are served by the /media/ route), but were never
    uploaded to Cloudinary -- so the Cloudinary URL for them 404s. Point those
    at the local copy; anything not on disk (new uploads) still goes to
    Cloudinary.
    """

    _local = FileSystemStorage()

    def url(self, name):
        if name and os.path.isfile(os.path.join(settings.MEDIA_ROOT, name)):
            return self._local.url(name)
        return super().url(name)


class LocalFirstRawStorage(LocalFirstMixin, RawMediaCloudinaryStorage):
    pass


class LocalFirstVideoStorage(LocalFirstMixin, VideoMediaCloudinaryStorage):
    pass
