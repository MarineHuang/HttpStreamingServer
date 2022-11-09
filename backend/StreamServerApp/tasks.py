# -*- coding: utf-8 -*-
from functools import wraps
from celery import shared_task
from celery.utils.log import get_task_logger
import traceback
from django.core.cache import cache

from StreamServerApp.models import Video, Series, Movie, Subtitle
from StreamServerApp.pcs_utils import BaiduPcsClient
from StreamServerApp.database_utils import update_db_from_local_folder
from StreamingServer import settings

logger = get_task_logger(__name__)

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


@shared_task
def sync_subtitles(subtitle_id):
    subtitle = Subtitle.objects.get(id=subtitle_id)
    subtitle.resync()
    return 0

@shared_task
def update_db_from_local_folder_async(keep_files=True):
    update_db_from_local_folder(
        scan_path=settings.FILE_STORAGE, 
        repository_path=settings.VIDEO_ROOT, 
        repository_url=settings.VIDEO_URL, 
        keep_files=True)
    cache.set("is_updating", "false", timeout=None)
    return 0

@shared_task(bind=True)
@skip_if_running
def sync_videos(self):
    cookies=""
    remote_urls=["/subtitle/"]

    try:
        panClient = BaiduPcsClient(cookies, remote_urls)
        ret = panClient.sync_videos()
        logger.info("task of sync videos success")
        logger.info("synchronized videos: {}".format(ret))
    except Exception as ex:
        logger.error("task of sync videos failed")
        traceback.print_exception(type(ex), ex, ex.__traceback__)

    return 0