from celery import shared_task
from StreamServerApp.models import Video, Series, Movie, Subtitle

#from functools import wraps
#from celery.utils.log import get_task_logger
#logger = get_task_logger(__name__)

#from StreamServerApp.pcs_utils import BaiduPcsClient
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


