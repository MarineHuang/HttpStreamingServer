# -*- coding: utf-8 -*-
import os
from enum import Enum, unique

@unique
class FileType(Enum):
    UNKNOWN = 0
    VIDEO = 1
    AUDIO = 2
    SUBTITLE = 3
    QUASI_SUBTITLE = 4

MEDIA_VIDEO_EXTS = ['mp4', 'avi', 'mkv', 'flv']
MEDIA_AUDIO_EXTS = ['mp3', 'aac', 'm4a']
MEDIA_SUBTITLE_EXTS = ['srt', 'ass', 'vtt']
MEDIA_QUASI_SUBTITLE_EXTS = ['txt', 'lrc']

def get_file_type(path) -> FileType:
    '''
    Args:
        path: path to file
    Return:
        file type: video, auido, subtile 
    '''
    _, ext = os.path.splitext(path)
    if ext and len(ext)>1:
        ext = ext[1:].lower()
        if ext in MEDIA_VIDEO_EXTS:
            return FileType.VIDEO
        elif ext in MEDIA_AUDIO_EXTS:
            return FileType.AUDIO
        elif ext in MEDIA_SUBTITLE_EXTS:
            return FileType.SUBTITLE
        elif ext in MEDIA_QUASI_SUBTITLE_EXTS:
            return FileType.QUASI_SUBTITLE
        else:
            return FileType.UNKNOWN
    else:
        return 'unknown'