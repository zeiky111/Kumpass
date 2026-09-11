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
