# Generated for module topics

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('signtext', '0045_pre_post_tests'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ModuleTopic',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=180)),
                ('content', models.TextField(blank=True, default='')),
                ('sign_words', models.JSONField(blank=True, default=list)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('module', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='topics', to='signtext.learningmodule')),
            ],
            options={
                'ordering': ['order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='ModuleTopicCompletion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('completed_at', models.DateTimeField(auto_now_add=True)),
                ('topic', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='completions', to='signtext.moduletopic')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='module_topic_completions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'topic')},
            },
        ),
    ]
