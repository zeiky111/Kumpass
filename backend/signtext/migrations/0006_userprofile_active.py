from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("signtext", "0005_modulefile"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="active",
            field=models.IntegerField(default=0),
        ),
    ]