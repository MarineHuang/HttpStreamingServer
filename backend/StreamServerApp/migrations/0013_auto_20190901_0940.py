# Generated by Django 2.2.3 on 2019-09-01 09:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('StreamServerApp', '0012_video_subtitle'),
    ]

    operations = [
        migrations.RenameField(
            model_name='video',
            old_name='subtitle',
            new_name='subtitle_url',
        ),
    ]