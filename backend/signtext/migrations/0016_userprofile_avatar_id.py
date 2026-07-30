# Generated manually to add only the avatar_id field, without bundling the
# unrelated pre-existing PendingEmailVerification model-state drift.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('signtext', '0015_signvideo_text_to_sign_only'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='avatar_id',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
    ]
