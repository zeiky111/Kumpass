# Generated manually: add photo field to UserProfile
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("signtext", "0007_userprofile_name_parts"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="photo",
            field=models.ImageField(upload_to="profile_photos/%Y/%m/%d/", null=True, blank=True),
        ),
    ]
