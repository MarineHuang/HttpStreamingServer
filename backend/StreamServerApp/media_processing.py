import os
import subprocess
import json

import re
import sys
import string
import datetime
import ffmpeg
import subliminal
from StreamServerApp.media_management.processing import *
from StreamServerApp.media_management.dash_packager import dash_packager
from StreamServerApp.media_management.fileinfo import createfileinfo, readfileinfo
from StreamingServer import settings

def prepare_video(video_full_path,
                  repository_local_path,
                  repository_remote_url,
                  keep_files=False):
    """ # Create thumbnail, transmux if necessayr and get all the videos infos.
        Args:
        video_full_path: full path to the video (eg: /usr/torrent/folder1/Dune.mp4)
        repository_local_path: path to the video repository (eg: /usr/Videos/)
        repository_remote_url: url to the video repository (eg: /Videos/)
        keep_files: Keep original files in case of convertion

        return: Dictionnary with video infos

        this functions will only add videos to the database if
        they are encoded with h264/AAC codec
    """
    print("processing {}".format(video_full_path))

    video_file_name_wo_ext = os.path.splitext(os.path.split(video_full_path)[-1])[0]
    # /usr/Videos/2022-10-15/Dune
    dash_output_directory = os.path.join(repository_local_path,
        datetime.datetime.now().strftime('%Y-%m-%d'),
        video_file_name_wo_ext
    )
    if os.path.exists(dash_output_directory):
        raise Exception("dash directory is exists: {}".format(dash_output_directory))
    else:
        os.makedirs(dash_output_directory)
    
    try:
        probe = ffmpeg.probe(video_full_path)
    except ffmpeg.Error as e:
        print(e.stderr, file=sys.stderr)
        raise

    if 'duration' in probe['format']:
        duration = float(probe['format']['duration'])
    
    video_height=0
    video_width=0
    video_codec_type=""
    audio_codec_type=""
    low_layer_bitrate=None
    low_layer_height=None
    high_layer_bitrate=None 
    high_layer_height=None
    video_elementary_stream_path_high_layer=None
    video_elementary_stream_path_low_layer=None
    audio_elementary_stream_path=None
    
    # audio stream
    audio_stream = next(
        (stream
         for stream in probe['streams'] if stream['codec_type'] == 'audio'),
        None)
    if audio_stream is None:
        #At the moment, if the input video has no audio, it's not added to the database.
        print('No audio stream found', file=sys.stderr)
    else:
        if 'duration' in audio_stream:
            duration = float(audio_stream['duration'])

        audio_elementary_stream_path = os.path.join(dash_output_directory,
            "{}.m4a".format(video_file_name_wo_ext)
        )

        audio_codec_type = audio_stream['codec_name']
        if "aac" in audio_codec_type:
            extract_audio(video_full_path, audio_elementary_stream_path)
        else:
            aac_encoder(video_full_path, audio_elementary_stream_path)
    
    # video stream
    video_stream = next(
        (stream
         for stream in probe['streams'] if stream['codec_type'] == 'video'),
        None)
    if video_stream is None:
        print('No video stream found', file=sys.stderr)
    else:
        video_codec_type = video_stream['codec_name']
        video_width = video_stream['width']
        video_height = video_stream['height']

        if 'duration' in video_stream:
            duration = float(video_stream['duration'])

        video_elementary_stream_path_high_layer = os.path.join(dash_output_directory,
            "{}_{}.264".format(video_file_name_wo_ext, video_height)
        )
        video_elementary_stream_path_low_layer = os.path.join(dash_output_directory,
            "{}_low.264".format(video_file_name_wo_ext)
        )

        high_layer_compression_ratio = int(os.getenv('HIGH_LAYER_COMPRESSION_RATIO_IN_PERCENTAGE', 7))
        high_layer_bitrate = int(video_width * video_height * \
            24 * 4 * (high_layer_compression_ratio/100.0))
        print("high_layer_bitrate = {}".format(high_layer_bitrate))
        high_layer_height = int(video_height)

        low_layer_bitrate = int(os.getenv('480P_LAYER_BITRATE', 400000))
        low_layer_height = int(video_height / 2.0)
        print("low_layer_bitrate = {}".format(low_layer_bitrate))

        #https://stackoverflow.com/questions/5024114/suggested-compression-ratio-with-h-264
        h264_encoder(video_full_path,
            video_elementary_stream_path_high_layer, 
            high_layer_height, 
            high_layer_bitrate
        )

        if low_layer_bitrate > 0:
            h264_encoder(video_full_path,
                video_elementary_stream_path_low_layer, 
                low_layer_height, 
                low_layer_bitrate
            )

    # subtitle stream
    webvtt_ov_fullpaths = []
    subtitles_index = 0 
    for stream in probe['streams']:
        if stream['codec_type'] == 'subtitle':
            webvtt_ov_fullpath_tmp = os.path.join(dash_output_directory,
                '{}_ov_{}.vtt'.format(video_file_name_wo_ext, subtitles_index)
            )
            
            print('found subtitles in the input stream of {}, and extract to {}'.format(
                video_full_path,
                webvtt_ov_fullpath_tmp
            ))
            
            extract_subtitle(video_full_path, webvtt_ov_fullpath_tmp, subtitles_index)
            webvtt_ov_fullpaths.append(webvtt_ov_fullpath_tmp)
            subtitles_index += 1
    
    # Thumbnail creation
    thumbnail_fullpath = "{}/thumbnail.jpeg".format(dash_output_directory)
    if video_stream:
        generate_thumbnail(video_full_path, duration, thumbnail_fullpath)
    else:
        thumbnail_fullpath = "{}/default_thumbnail.jpeg".format(settings.VIDEO_ROOT)
    
    # Dash_packaging
    mpd_full_path = "{}/playlist.mpd".format(dash_output_directory)
    dash_packager(video_elementary_stream_path_low_layer, low_layer_bitrate, low_layer_height,
                  video_elementary_stream_path_high_layer, high_layer_bitrate, high_layer_height, 
                  audio_elementary_stream_path,
                  mpd_full_path)
    
    if video_elementary_stream_path_high_layer:
        os.remove(video_elementary_stream_path_high_layer)
    if video_elementary_stream_path_low_layer:
        os.remove(video_elementary_stream_path_low_layer)
    if audio_elementary_stream_path:
        os.remove(audio_elementary_stream_path)
    if not keep_files:
        os.remove(video_full_path)

    relative_path = os.path.relpath(mpd_full_path, repository_local_path)
    remote_video_url = os.path.join(repository_remote_url, relative_path)

    thumbnail_relativepath = os.path.relpath(thumbnail_fullpath, repository_local_path)
    remote_thumbnail_url = os.path.join(repository_remote_url, thumbnail_relativepath)

    video_info = {
        'video_height': video_height,
        'video_width': video_width,
        'video_codec_type': video_codec_type,
        'audio_codec_type': audio_codec_type,
        'remote_video_url': remote_video_url,
        'remote_thumbnail_url': remote_thumbnail_url,
        'ov_subtitles': webvtt_ov_fullpaths,
        'mpd_path': mpd_full_path,
        'video_full_path': video_full_path,
    }

    #File info creation
    fileinfo_path = "{}/fileinfo.json".format(dash_output_directory)
    createfileinfo(fileinfo_path, video_info)

    return video_info


def get_video_type_and_info(video_path):
    """ # Uses subliminal to parse information from filename.

    Subliminal tells us if the video is a serie or not.
    If not, we assume it to be a movie, which is not necesarly the case (e.g. documentary, simple video).
    We use string.capwords() on title strings for consistency of capitalization.
    The subliminal fromname function as a bug when the input string begins with 1-, as a quick fix, we use a regular expression to
    get rid of the problematic characters. A future fix coulb be to be use imdb api for disambiguation.

    Args:
    video_path: full path to the video (eg: /Videos/folder1/video.mp4)

    Returns: dict containing video type and info

    """
    filename = os.path.basename(video_path)
    if re.match(r'(\d*(\-|\.) .*)', filename):
        filename = re.sub(r'(\d*(\-|\.) )', '', filename, 1)
    try:
        video = subliminal.Video.fromname(filename)
    except ValueError:
        #This usually happens when there is not enough data for subliminal to guess.
        return {
            'type': 'Movie',
            'title': string.capwords(filename),
        }

    if hasattr(video, 'series'):
        return {
            'type': 'Series',
            'title': string.capwords(video.series),
            'season': video.season,
            'episode': video.episode,
        }
    elif hasattr(video, 'title'):
        return {
            'type': 'Movie',
            'title': string.capwords(video.title),
        }
