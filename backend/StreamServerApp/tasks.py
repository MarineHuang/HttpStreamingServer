from celery import shared_task
from StreamServerApp.models import Video, Series, Movie, Subtitle
from StreamServerApp.media_processing import convert_subtitles_to_webvtt
from StreamServerApp.database_utils import update_db_from_local_folder
import subprocess
import os
from django.conf import settings



@shared_task
def sync_subtitles( video_id, subtitle_id):
    video = Video.objects.get(id=video_id)
    video_path = os.path.join(settings.VIDEO_ROOT, video.video_url.split(settings.VIDEO_URL)[1])
    #print(video_path)
    assert(os.path.isfile(video_path))
    subtitle = Subtitle.objects.get(id=subtitle_id)
    subtitle_path = subtitle.srt_path
    assert(os.path.isfile(subtitle_path))
    webvtt_path = subtitle.vtt_path.replace('.vtt', '_sync.vtt')
    #print(webvtt_path)
    sync_subtitle_path = subtitle_path.replace('.srt', '_sync.srt')
    subprocess.run(["ffs", video_path, "-i", subtitle_path, "-o", sync_subtitle_path])
    convert_subtitles_to_webvtt(sync_subtitle_path, webvtt_path)
    subtitle.srt_sync_path = sync_subtitle_path
    subtitle.vtt_sync_path = webvtt_path
    subtitle.webvtt_sync_url = os.path.join(settings.VIDEO_URL, webvtt_path.split(settings.VIDEO_ROOT)[1])
    #print(subtitle.webvtt_sync_url )
    subtitle.save()
