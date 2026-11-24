"""Module certificates become "Certificate of Achievement".

Points existing module Certificate catalog entries at the new template and
renames them. Certificates already issued (their PDFs) are left as they are.
"""

from django.db import migrations

OLD_TEMPLATE = "images/modulecert.png"
NEW_TEMPLATE = "images/modulecert-achievement.png"
OLD_SUFFIX = "Certificate of Completion"
NEW_SUFFIX = "Certificate of Achievement"


def forwards(apps, schema_editor):
    Certificate = apps.get_model("signtext", "Certificate")
    for cert in Certificate.objects.filter(module__isnull=False):
        cert.template_path = NEW_TEMPLATE if cert.template_path == OLD_TEMPLATE else cert.template_path
        if cert.title.endswith(OLD_SUFFIX):
            cert.title = cert.title[: -len(OLD_SUFFIX)] + NEW_SUFFIX
        cert.save(update_fields=["template_path", "title"])


def backwards(apps, schema_editor):
    Certificate = apps.get_model("signtext", "Certificate")
    for cert in Certificate.objects.filter(module__isnull=False):
        cert.template_path = OLD_TEMPLATE if cert.template_path == NEW_TEMPLATE else cert.template_path
        if cert.title.endswith(NEW_SUFFIX):
            cert.title = cert.title[: -len(NEW_SUFFIX)] + OLD_SUFFIX
        cert.save(update_fields=["template_path", "title"])


class Migration(migrations.Migration):

    dependencies = [
        ("signtext", "0046_module_topics"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
