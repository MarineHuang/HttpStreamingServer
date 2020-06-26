# Generated by Django 2.2.8 on 2020-05-27 11:02

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('StreamServerApp', '0018_auto_20200207_1049'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserVideoHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time', models.IntegerField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('video', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='StreamServerApp.Video')),
            ],
        ),
        migrations.AddField(
            model_name='video',
            name='history',
            field=models.ManyToManyField(through='StreamServerApp.UserVideoHistory', to=settings.AUTH_USER_MODEL),
        ),
    ]