# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import uuid
import traceback
from typing import Optional, List, Dict, Any, Callable
from types import SimpleNamespace

from django.db import transaction
from StreamingServer import settings
from StreamServerApp.models import Video, Series, Movie, Subtitle
from StreamServerApp.media_management.utils import FileType, get_file_type
from StreamServerApp.database_utils import add_one_video_to_database


from baidupcs_py.baidupcs import BaiduPCSApi, PCS_UA
from baidupcs_py.utils import human_size_to_int
#from baidupcs_py.commands.list_files import list_files as BaiduListFiles

def file_rename(src_name):
    dst_name = src_name.replace(' ', '_')
    return dst_name

class DownloadParams(SimpleNamespace):
    concurrency: int = 5
    chunk_size: str = str(1 * 1024 * 1024)
    quiet: bool = False

DEFAULT_DOWNLOADPARAMS = DownloadParams()

class BaiduPcsClient():
    def __init__(self, cookies: str, remote_urls: list):
        
        self.cookies = dict([c.split("=", 1) for c in cookies.split("; ")])
        self.bduss = self.cookies.get("BDUSS")
        self.api = BaiduPCSApi(bduss=self.bduss, cookies=self.cookies)
        self.downloadparams = DEFAULT_DOWNLOADPARAMS
        self.remote_urls = remote_urls
        self.destination_dir = str(settings.FILE_STORAGE)

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

    def aget_py_cmd(
        self,
        url: str,
        localpath: str
    ):
        _ck = f"Cookie: BDUSS={self.bduss};"

        # This is an error of aget-py
        chunk_size = human_size_to_int(self.downloadparams.chunk_size)

        cmd = [
            "aget",
            url,
            "-o",
            localpath,
            "-H",
            f"User-Agent: {PCS_UA}",
            "-H",
            "Connection: Keep-Alive",
            "-H",
            _ck,
            "-s",
            str(self.downloadparams.concurrency),
            "-k",
            str(chunk_size),
        ]
        return cmd

    def download_file(self, remote_path):
        dlink = self.api.download_link(remote_path)
        if not dlink:
            print("get download link failed for : {}".format(remote_path))
            return None
        
        #file_extension = os.path.splitext(os.path.basename(remote_path))[1]
        #download_filename =  "{}{}".format(str(uuid.uuid1()), file_extension)
        download_filename = file_rename(os.path.basename(remote_path))
        local_path = os.path.join(self.destination_dir, download_filename)
        localpath_tmp = local_path + ".tmp"
        print(f"[italic blue]Download[/italic blue]: {remote_path} to {local_path}")

        cmd = self.aget_py_cmd(url=dlink, localpath=localpath_tmp)
        #print("download command {}".format(cmd))
        child = subprocess.run(cmd, stdout=subprocess.DEVNULL if self.downloadparams.quiet else None)
        if child.returncode != 0:
            print(
                f"[italic]{cmd}[/italic] fails. return code: [red]{child.returncode}[/red]"
            )
            return None
        else:
            shutil.move(localpath_tmp, local_path)
            return local_path

    def sync_videos(self):
        downloaded_files=[]
        all_files = self.walk()

        for pcs_file in all_files:
            file_type = get_file_type(pcs_file.path)
            if FileType.UNKNOWN == file_type:
                print("skip downloading {} because unknown file type".format(pcs_file.path))
                continue
            
            file_name = os.path.basename(pcs_file.path)
            dest_path = os.path.join(self.destination_dir, file_rename(file_name))
            if os.path.exists(dest_path):
                print("skip downloading {} because destination path exists".format(pcs_file.path))
                continue
            
            print("begin to download: {}".format(pcs_file.path))
            try:
                local_path = self.download_file(remote_path=pcs_file.path)
            except Exception as ex:
                traceback.print_exception(type(ex), ex, ex.__traceback__)
            finally:
                if local_path:
                    print("download success: {} -> {}".format(pcs_file.path, local_path))
                    downloaded_files.append((pcs_file.path, local_path))
                    if FileType.SUBTITLE == file_type:
                        video_set = Video.objects.search_trigramm('name', file_name)\
                            .select_related('movie', 'series').all()
                        for v in video_set:
                            print("video named {} try to get subtitles".format(v.name))
                            v.get_subtitles(settings.VIDEO_ROOT, settings.VIDEO_URL) 
                    
                    elif FileType.VIDEO == file_type or FileType.AUDIO == file_type:
                        with transaction.atomic():
                            add_one_video_to_database(
                                    full_path=local_path, 
                                    repository_path=settings.VIDEO_ROOT, 
                                    repository_url=settings.VIDEO_URL, 
                                    filename=file_name,
                                    keep_files=True
                            )
                else:
                    print("download failed: {}".format(pcs_file.path))
            
        return downloaded_files
