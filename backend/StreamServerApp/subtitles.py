import os
from babelfish import Language
from subliminal import Video, subtitle, region, download_best_subtitles, save_subtitles
import io
from StreamingServer import settings
from StreamServerApp.media_management.utils import FileType, get_file_type
from StreamServerApp.media_processing import extract_subtitle, convert_subtitles_to_webvtt
from AIServiceApp.transcription import transcript_media_file
from AIServiceApp.subtitle_aligner import force_align

#https://subliminal.readthedocs.io/en/latest/user/usage.html


def init_cache():
    """ # init cache for subtitles database query and stuff.
    """
    if not os.path.isfile('cachefile.dbm.db'):
        print("Create subtitles cache data")
        region.configure('dogpile.cache.dbm', arguments={
            'filename': 'cachefile.dbm'}, replace_existing_backend=True)


def remove_nullcharacters(fname):
    flist = open(fname).readlines()
    output = []
    for s in flist:
        output.append(s.replace('\0', ''))
    return output


def handle_subliminal_download(video, video_path, languages_to_retrieve):
    """ # Download the best subtitles in french and english
        Args:
        video : Name of video
        video_path: absolute path to videos
        languages_to_retrieve : dict of subtitles languages to retrieve
        return : two dicts with the path of each subtitles with str of language as key / Exemple : 'eng' for english, 'fra' for french .
        the first dict is the path to vtt subtitles, the second one is the path to str subtitles
    """

    webvtt_subtitles_returned = {}
    srt_subtitles_returned = {}
    best_subtitles = download_best_subtitles(
        [video], set(map(Language, languages_to_retrieve)))
    if best_subtitles[video]:
        for retrieved_subtitle in best_subtitles[video]:
            subtitles_are_saved = save_subtitles(
                video, [retrieved_subtitle], encoding='utf8')
            if subtitles_are_saved:
                srt_fullpath = subtitle.get_subtitle_path(
                    video_path, retrieved_subtitle.language)
                srt_subtitles_returned[
                    retrieved_subtitle.language.alpha3] = srt_fullpath
                new_data = remove_nullcharacters(srt_fullpath)
                with io.open(srt_fullpath, 'w', encoding='utf-8') as f:
                    for line in new_data:
                        f.write(line)
                webvtt_fullpath = os.path.splitext(srt_fullpath)[0]+'.vtt'
                if os.path.isfile(webvtt_fullpath):
                    # Add the subtitles path to subtitles_returned even if they are already downloaded/converted
                    webvtt_subtitles_returned[
                        retrieved_subtitle.language.alpha3] = webvtt_fullpath
                if os.path.isfile(srt_fullpath):
                    # Add the subtitles path to subtitles_returned after converting them in .vtt
                    convert_subtitles_to_webvtt(srt_fullpath, webvtt_fullpath)
                    webvtt_subtitles_returned[
                        retrieved_subtitle.language.alpha3] = webvtt_fullpath
    return webvtt_subtitles_returned, srt_subtitles_returned


def get_subtitles(video_path, video_folder=None):
    """ # get subtitles and convert them to web vtt
        Args:
        video_path: absolute path to videos
        return: empty string if no subtitles was found. Otherwise return dict of subtitle absolute location with str(Language) as key
    """
    print("get_subtitle function: video_path={}, video_folder={}".format(video_path, video_folder))
    languages_to_retrieve = {
        'eng',
        'fra',
    }
    webvtt_fullpath = {}
    srt_fullpath = {}
    
    # step1: try search subtitle from local disk
    video_filename, video_ext = os.path.splitext(os.path.basename(video_path))

    for root, _, files in os.walk(settings.FILE_STORAGE):
        for f in files:
            if not f.startswith(video_filename):
                continue

            srt_file_path = None
            if FileType.SUBTITLE == get_file_type(f):
                srt_file_path = os.path.join(root, f)
            elif FileType.QUASI_SUBTITLE == get_file_type(f):
                srt_file_path = os.path.join(root, video_filename+'.srt')
                generate_subtitle_by_force_align(
                    media_file=video_path,
                    quasi_subtitle_file=os.path.join(root, f),
                    output_subtitle_file=srt_file_path
                )

            if srt_file_path is None:
                continue

            srt_fullpath['eng'] = srt_file_path 
            webvtt_file_name = os.path.splitext(os.path.basename(srt_file_path))[0] + '.vtt'
            
            if video_folder is None:
                webvtt_file_path = os.path.join(settings.VIDEO_ROOT, webvtt_file_name)
            else:
                webvtt_file_path = os.path.join(video_folder, webvtt_file_name)
            
            convert_subtitles_to_webvtt(srt_file_path, webvtt_file_path)
            webvtt_fullpath['eng'] = webvtt_file_path

            return [webvtt_fullpath, srt_fullpath]

    # step2: try download subtitle from subliminal
    #try:
    #    video = Video.fromname(video_path)
    #    try:
    #        webvtt_fullpath, srt_fullpath = handle_subliminal_download(
    #            video, video_path, languages_to_retrieve)
    #    except:
    #        webvtt_fullpath = {}
    #        srt_fullpath = {}
    #except ValueError:
    #    #This usually happens when there is not enough data for subliminal to guess
    #    pass

    return [webvtt_fullpath, srt_fullpath]


def generate_subtitle_by_force_align(
                    media_file: str,
                    quasi_subtitle_file: str,
                    output_subtitle_file: str
                ) -> bool:
    '''
    通过force align为音视频生成字幕
    Args:
        media_file: 音视频文件路径
        quasi_subtitle_file: 准字幕文件路径, 即断好句的纯文本文件
        output_subtitle_file: 生成的字幕文件
    '''
    print(f'generate subtitle by force align: media is {media_file}, quasi subtitle is {quasi_subtitle_file}')
    # 音视频转写
    transcription_result = transcript_media_file(media_file)
    if transcription_result is None:
        print(f"transcript for {media_file} failed")
        return False
    force_align(transcription_result, quasi_subtitle_file, output_subtitle_file)
    print(f'generate subtitle by force align success, output subtitle file {output_subtitle_file}')
    return True
