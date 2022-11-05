from celery import shared_task
from StreamServerApp.models import Video, Series, Movie, Subtitle

from functools import wraps
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from StreamServerApp.pcs_utils import BaiduPcsClient
#from StreamingServer import settings as AppSettings
#from StreamServerApp.database_utils import update_db_from_local_folder
#from django.core.cache import cache

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
def sync_videos(self):
    cookies=""
    remote_urls=["/shared/"]

    try:
        panClient = BaiduPcsClient(cookies, remote_urls)
        ret = panClient.sync_videos()
        logger.info("sync videos success: {}".format(ret))
        #if len(ret) > 0:
        #    update_db_from_local_folder(
        #        scan_path="/usr/torrent/", 
        #        repository_path=AppSettings.VIDEO_ROOT, 
        #        repository_url=AppSettings.VIDEO_URL, 
        #        keep_files=True)
        #    cache.set("is_updating", "false", timeout=None)
    except Exception as e:
        logger.error("error occurs when sync videos: {}".format(e))

    return 0