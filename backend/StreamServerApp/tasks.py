from celery import shared_task, task
from StreamServerApp.models import Video, Series, Movie, Subtitle
import subprocess
import os
from django.conf import settings
from functools import wraps
import time

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

@shared_task
def sync_subtitles(subtitle_id):
    subtitle = Subtitle.objects.get(id=subtitle_id)
    subtitle.resync()
    return 0


@shared_task
def get_subtitles_async(video_id, video_path, remote_url):
    video = Video.objects.get(id=video_id)
    video.get_subtitles(video_path, remote_url)
    return 0


def skip_if_running(f):
    task_name = f'{f.__module__}.{f.__name__}'

    @wraps(f)
    def wrapped(self, *args, **kwargs):
        workers = self.app.control.inspect().active()

        for worker, tasks in workers.items():
            for task in tasks:
                if (task_name == task['name'] and
                        tuple(args) == tuple(task['args']) and
                        kwargs == task['kwargs'] and
                        self.request.id != task['id']):
                    
                    print(f'task {task_name} ({args}, {kwargs}) is running on {worker}, skipping')
                    return None

        return f(self, *args, **kwargs)

    return wrapped


@shared_task(bind=True)
@skip_if_running
def sync_video(self):
    time.sleep(70)
    logger.info("sync video from network storage")