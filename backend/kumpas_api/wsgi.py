import os
import logging

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kumpas_api.settings")

application = get_wsgi_application()

# Render's build/start commands are configured outside this repo, and the
# migrate step has been missed there before (see git history), leaving the
# DB schema behind the models. Running migrate here, once per process boot,
# means a deploy can never again ship code whose migrations didn't apply --
# it's idempotent, so this is a no-op once the schema is already current.
try:
    from django.core.management import call_command

    call_command("migrate", interactive=False, verbosity=1)
except Exception:
    logging.getLogger(__name__).exception("Startup migrate failed")

# If the database comes up with no sign videos at all (fresh/reset DB), put
# the bundled library back so Browse Signs, Text-to-Sign and the Games
# aren't left empty. Skipped whenever any row exists, so it never fights
# admin edits or deletions.
try:
    from signtext.management.commands.restore_sign_videos import restore_sign_videos

    restored = restore_sign_videos(only_if_empty=True)
    if restored:
        logging.getLogger(__name__).warning("Restored %d sign videos into an empty database", restored)
except Exception:
    logging.getLogger(__name__).exception("Startup sign video restore failed")
