# -*- coding: utf-8 -*-
"""Streaming server module utilies

This module provides functionalities to erase/update videos infos in the database

Todo:
    * Define how to interact with multiple servers
"""
import os
from functools import wraps
import traceback

from celery import shared_task
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from django.db import transaction
from django.core.cache import cache

from StreamServerApp.models import Video, Series, Movie, Subtitle
from StreamServerApp.subtitles import init_cache

from StreamServerApp.media_management.fileinfo import createfileinfo, readfileinfo
from StreamServerApp.media_processing import prepare_video, get_video_type_and_info
from StreamServerApp.tasks import get_subtitles_async
from StreamingServer import settings as AppSettings

from baidupcs_py.baidupcs import BaiduPCSApi
from baidupcs_py.commands.download import download_file, Downloader, DownloadParams
#from baidupcs_py.commands.list_files import list_files as BaiduListFiles

def delete_DB_Infos():
    """ delete all videos, movies and series in the db
    """
    Video.objects.all().delete()
    Movie.objects.all().delete()
    Series.objects.all().delete()


def get_num_videos():
    """ Return the number of videos in the db
    """
    return Video.objects.count()


def update_db_from_local_folder(scan_path, repository_path, repository_url, keep_files=True):
    """ #  Update  the videos infos in the database
        Args:
        scan_path: Local Folder where the videos are stored
        repository_path: path to the video repository (eg: /usr/Videos/)
        repository_url: url to the video repository (eg: /Videos/)

        this functions will only add videos to the database if
        they are encoded with h264 codec
    """

    init_cache()
    idx = 0
    count_series = 0
    count_movies = 0

    database_old_files = Video.objects.values_list('video_folder', 'id')
    old_path_set = set()
    #We check here if old database files are still present on filesystem, if not, delete from db
    video_ids_to_delete = []

    for old_files_path, old_video_id in database_old_files:
        if os.path.isfile(old_files_path) is False:
            print(old_files_path + "will be deleted")
            video_ids_to_delete.append(old_video_id)
        else:
            old_path_set.add(old_files_path)

    Video.objects.filter(pk__in=video_ids_to_delete).delete()
    #Remove empty Series/Movies dataset
    Series.objects.filter(video=None).delete()
    Movie.objects.filter(video=None).delete()

    num_video_before = get_num_videos()

    for root, directories, filenames in os.walk(scan_path):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            if full_path in old_path_set:
                print(full_path + " is already in db, skip it")
                continue

            if os.path.isfile(full_path) and (full_path.endswith(".mp4")
                                      or full_path.endswith(".mkv")
                                      or full_path.endswith(".avi")):
                try:
                    # Atomic transaction in order to make all occur or nothing occurs in case of exception raised
                    with transaction.atomic():
                        created = add_one_video_to_database(
                            full_path, repository_path, repository_url, filename,
                            keep_files)
                        if created == 1:
                            count_movies += 1
                        elif created == 2:
                            count_series += 1

                except Exception as ex:
                    print("An error occured")
                    traceback.print_exception(type(ex), ex, ex.__traceback__)
                    continue
            elif os.path.isfile(full_path) and (full_path.endswith(".mpd")):
                try:
                    # Atomic transaction in order to make all occur or nothing occurs in case of exception raised
                    with transaction.atomic():
                        retValue = add_one_manifest_to_database(
                            full_path, repository_path, repository_url, filename,
                            keep_files)
                        if retValue == 1:
                            count_movies += 1
                        elif retValue == 2:
                            count_series += 1

                except Exception as ex:
                    print("An error occured")
                    traceback.print_exception(type(ex), ex, ex.__traceback__)
                    continue

    num_video_after = get_num_videos()

    print("{} videos were added to the database".format(num_video_after -
                                                        num_video_before))
    print('{} series and {} movies were created'.format(
        count_series, count_movies))


def add_one_video_to_database(full_path,
                              repository_path,
                              repository_url,
                              filename,
                              keep_files=False):
    """ # create infos in the database for one video

        Args:
        full_path: absolue path to the video
        repository_path: path to the video repository (eg: /usr/Videos/)
        repository_url: url to the video repository (eg: /Videos/)
        keep_files: Keep files in case of convertion

        return 0 if noseries/movies was created, 1 if a movies was created, 2 if a series was created

    """
    video_infos = prepare_video(full_path, repository_path, repository_url,
                                keep_files)
    if not video_infos:
        print("video infos are empty, don't add to database")
        return 0

    v = Video(
        name=filename,
        video_folder=video_infos['mpd_path'],
        video_url=video_infos['remote_video_url'],
        video_codec=video_infos['video_codec_type'],
        audio_codec=video_infos['audio_codec_type'],
        height=video_infos['video_height'],
        width=video_infos['video_width'],
        thumbnail=video_infos['remote_thumbnail_url'],
    )

    # parse movie or series, episode & season
    return_value = 0
    video_type_and_info = get_video_type_and_info(filename)

    if video_type_and_info:
        if video_type_and_info['type'] == 'Series':
            series, created = Series.objects.get_or_create(
                title=video_type_and_info['title'],
                defaults={'thumbnail': video_infos['remote_thumbnail_url']})
            v.series = series
            v.season = video_type_and_info['season']
            v.episode = video_type_and_info['episode']

            if created:
                return_value = 2

        elif video_type_and_info['type'] == 'Movie':
            movie, created = Movie.objects.get_or_create(
                title=video_type_and_info['title'])
            v.movie = movie

            if created:
                return_value = 1

        v.save()
        for ov_subtitle_path in video_infos["ov_subtitles"]:
            ov_sub = Subtitle()
            webvtt_subtitles_relative_path = os.path.relpath(
                ov_subtitle_path, repository_path)
            ov_sub.webvtt_subtitle_url = os.path.join(
                repository_url, webvtt_subtitles_relative_path)
            ov_sub.language = Subtitle.OV
            ov_sub.video_id = v
            ov_sub.save()

        #we use oncommit because autocommit is not enabled.
        transaction.on_commit(lambda: get_subtitles_async.delay(
            v.id, repository_path, repository_url))

    return return_value


def add_one_manifest_to_database(full_path,
                                 repository_path,
                                 repository_url,
                                 filename,
                                 keep_files=False):
    """ # create infos in the database for one manifest

        Args:
        full_path: absolue path to the video
        repository_path: relative (to root) basepath (ie directory) containing video
        root: absolute path to directory containing all the videos
        repository_url: baseurl for video access on the server
        keep_files: Keep files in case of convertion

        return 0 if noseries/movies was created, 1 if a movies was created, 2 if a series was created

    """

    video_infos = []
    fileinfos_path = "{}/fileinfo.json".format(os.path.split(full_path)[0])
    if os.path.isfile(fileinfos_path):
        video_infos = readfileinfo(fileinfos_path)
        if not video_infos:
            print("video infos are empty, don't add to database")
            return 0
    else:
        return 0

    print("video_infos = {}".format(video_infos))

    filename = os.path.split(video_infos['video_full_path'])[1]

    print("filename = {}".format(filename))

    v = Video(
        name=filename,
        video_folder=full_path,
        video_url=video_infos['remote_video_url'],
        video_codec=video_infos['video_codec_type'],
        audio_codec=video_infos['audio_codec_type'],
        height=video_infos['video_height'],
        width=video_infos['video_width'],
        thumbnail=video_infos['remote_thumbnail_url'],
    )

    # parse movie or series, episode & season
    return_value = 0
    video_type_and_info = get_video_type_and_info(filename)

    if video_type_and_info:
        if video_type_and_info['type'] == 'Series':
            series, created = Series.objects.get_or_create(
                title=video_type_and_info['title'],
                defaults={'thumbnail': video_infos['remote_thumbnail_url']})
            v.series = series
            v.season = video_type_and_info['season']
            v.episode = video_type_and_info['episode']

            if created:
                return_value = 2

        elif video_type_and_info['type'] == 'Movie':
            movie, created = Movie.objects.get_or_create(
                title=video_type_and_info['title'])
            v.movie = movie

            if created:
                return_value = 1

        v.save()

        #we use oncommit because autocommit is not enabled.
        transaction.on_commit(lambda: get_subtitles_async.delay(
            v.id, repository_path, repository_url))

    return return_value


def populate_db_from_remote_server(remotePath, ListOfVideos):
    """ # tobeDone
       ListOfVideos could be provided through an API Call
    """



@shared_task
def update_db_from_local_folder_async(keep_files=True):
    update_db_from_local_folder(
        scan_path="/usr/torrent/", 
        repository_path=AppSettings.VIDEO_ROOT, 
        repository_url=AppSettings.VIDEO_URL, 
        keep_files=True)
    cache.set("is_updating", "false", timeout=None)
    return 0



class BaiduPcsClient():
    def __init__(self, cookies: str, remote_urls: list):
        
        self.cookies = dict([c.split("=", 1) for c in cookies.split("; ")])
        self.bduss = self.cookies.get("BDUSS")
        self.api = BaiduPCSApi(bduss=self.bduss, cookies=self.cookies)
        self.remote_urls = remote_urls
        self.destination_dir = "/usr/torrent/"

    def list_files(self, remote_url):
        '''
        return network pan's file, only file, not include directory
        '''
        pcs_files = []
        for pcs_file in self.api.list(remote_url):
            if pcs_file.is_dir:
                pcs_files.extend(self.list_files(pcs_file.path))
            else:
                pcs_files.append(pcs_file)
        
        return pcs_files

    def walk(self):
        all_files = []
        for remote_url in self.remote_urls:
            all_files.extend(self.list_files(remote_url))
        return all_files


    def sync_videos(self):
        all_files = self.walk()

        downloaded_files=[]
        for pcs_file in all_files:
            file_name = os.path.basename(pcs_file.path)
            if not os.path.exists(os.path.join(self.destination_dir, file_name)) \
                and (file_name.endswith(".mp4")
                     or file_name.endswith(".mkv")
                     or file_name.endswith(".avi")
                     or file_name.endswith(".srt")
                     or file_name.endswith(".ass")
                     or file_name.endswith(".vtt")):
                print("begin to download: {}".format(pcs_file.path))
                try:
                    download_file(
                        api=self.api, 
                        remotepath=pcs_file.path,
                        localdir=self.destination_dir,
                        downloader=Downloader.aget_py,
                        downloadparams=DownloadParams(
                            concurrency=5, 
                            chunk_size=str(50 * 1024 * 1024), 
                            quiet=False),
                        out_cmd = False,
                        )
                    print("download success: {}".format(pcs_file.path))
                    downloaded_files.append(os.path.join(self.destination_dir, file_name))
                except Exception as e:
                    print("error occurs when downloading {}".format(pcs_file.path))
                    raise e

        return downloaded_files





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
    remote_urls=["/subtitle/"]

    try:
        panClient = BaiduPcsClient(cookies, remote_urls)
        ret = panClient.sync_videos()
        logger.info("sync videos success: {}".format(ret))
        if len(ret) > 0:
            update_db_from_local_folder(
                scan_path="/usr/torrent/", 
                repository_path=AppSettings.VIDEO_ROOT, 
                repository_url=AppSettings.VIDEO_URL, 
                keep_files=True)
            cache.set("is_updating", "false", timeout=None)
    except Exception as e:
        logger.error("error occurs when sync videos: {}".format(e))

    return 0
