import os
from babelfish import Language
from subliminal import Video, subtitle, region, download_best_subtitles, save_subtitles
import io
from StreamingServer import settings
from StreamServerApp.media_management.utils import FileType, get_file_type
from StreamServerApp.media_processing import extract_subtitle, convert_subtitles_to_webvtt
from StreamServerApp.utils import get_file_language, get_file_language_byname
from AIServiceApp.transcription import transcript_media_file
from AIServiceApp.subtitle_aligner import force_align
import json

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
    
    webvtt_dict = {}
    srt_dict = {}
    
    # step1: try search subtitle from local disk
    video_filename, video_ext = os.path.splitext(os.path.basename(video_path))

    for root, _, files in os.walk(settings.FILE_STORAGE):
        for f in files:
            if not f.startswith(video_filename):
                continue

            srt_file_path = None
            language = None # 'eng', 'chi', 'fri'

            if FileType.SUBTITLE == get_file_type(f):
                # f文件是srt ass等字幕文件
                srt_file_path = os.path.join(root, f)
                language = get_file_language_byname(os.path.join(root, f))
            elif FileType.QUASI_SUBTITLE == get_file_type(f):
                # f文件是断好句的字幕文件
                language = get_file_language(os.path.join(root, f))

                srt_file_path = os.path.join(root, video_filename+'.srt')
                trans_file_path = os.path.join(root, video_filename+'.trans')
                if os.path.exists(trans_file_path):
                    print(f'generate subtitle by adding time stamp')
                    add_time_stamp(
                        transcription_result=trans_file_path,
                        text=os.path.join(root, f),
                        output_subtitle_path=srt_file_path
                    )
                else:
                    print(f'generate subtitle by transcript')
                    generate_subtitle_by_transcript(
                        media_file=video_path,
                        text=os.path.join(root, f),
                        output_subtitle_path=srt_file_path,
                        trans_file = trans_file_path
                    )

            if srt_file_path is None \
                or not os.path.exists(srt_file_path):
                continue

            # default language is English
            if language is None:
                language = 'eng'

            if language in webvtt_dict.keys() \
                or language in srt_dict.keys():
                print(f"{language} subtitle exists already for {video_path}")
                continue

            webvtt_file_name = os.path.splitext(os.path.basename(srt_file_path))[0] + '.vtt'
            if video_folder is None:
                webvtt_file_path = os.path.join(settings.VIDEO_ROOT, webvtt_file_name)
            else:
                webvtt_file_path = os.path.join(video_folder, webvtt_file_name)
            
            convert_subtitles_to_webvtt(srt_file_path, webvtt_file_path)
            
            srt_dict[language] = srt_file_path
            webvtt_dict[language] = webvtt_file_path

            print(f"get {language} subtitle success: {srt_file_path} -> {video_path}")

    # step2: try download subtitle from subliminal
    #languages_to_retrieve = {
    #    'eng',
    #    'fra',
    #}
    #try:
    #    video = Video.fromname(video_path)
    #    try:
    #        webvtt_dict, srt_dict = handle_subliminal_download(
    #            video, video_path, languages_to_retrieve)
    #    except:
    #        webvtt_dict = {}
    #        srt_dict = {}
    #except ValueError:
    #    #This usually happens when there is not enough data for subliminal to guess
    #    pass

    if 0 == len(webvtt_dict.keys()) and 0 == len(srt_dict.keys()):
        print(f"get no subtitle for {video_path}")
    
    return [webvtt_dict, srt_dict]


def add_time_stamp(transcription_result,
                text,
                output_subtitle_path: str
                ):
    '''
    添加时间戳生成字幕
    Args:
        transcription_result: 音视频文件的转写结果(类型dict)，或者文件路径
        text: 断好句的没有时间戳的字幕(类型list(str)), 或者文件路径
        output_subtitle_path: 生成的字幕文件路径
    '''
    force_align(transcription_result, text, output_subtitle_path)
    print(f'generate subtitle by adding time stamp, \
output subtitle file: {output_subtitle_path}')
    return True

def generate_subtitle_by_transcript(
                    media_file: str,
                    text,
                    output_subtitle_path: str,
                    trans_file: str
                ) -> bool:
    '''
    通过语音识别为音视频生成字幕
    Args:
        media_file: 音视频文件路径
        text: 断好句的没有时间戳的字幕(类型list(str)), 或者文件路径
        output_subtitle_path: 生成的字幕文件路径
        trans_file: 音视频文件的转写结果保存路径
    '''
    # 音视频转写
    transcription_result = transcript_media_file(media_file)
    if transcription_result is None:
        print(f"transcript for {media_file} failed")
        return False
    else:
        print(f"transcript for {media_file} success")
        with open(trans_file, "w") as fp:
            print(f"save transcript result to {trans_file}")
            json.dump(transcription_result, fp)

        add_time_stamp(transcription_result, text, output_subtitle_path)
        print(f'generate subtitle by transcript success, \
output subtitle file: {output_subtitle_path}')
        return True
