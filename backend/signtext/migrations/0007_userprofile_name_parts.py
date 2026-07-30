from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("signtext", "0006_userprofile_active"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="first_name",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="middle_name",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="last_name",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="suffix",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
    ]
