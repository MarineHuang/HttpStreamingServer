# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import uuid
import traceback
from collections import namedtuple
from typing import Optional, List, Dict, Any, Callable, Union, Iterator, Tuple
from types import SimpleNamespace

from django.db import transaction
from django.db.models import Max, Min, Avg, Sum, Count
from StreamingServer import settings
from StreamServerApp.models import Video, Series, Movie, Subtitle
from StreamServerApp.media_management.utils import FileType, get_file_type
from StreamServerApp.database_utils import add_one_video_to_database


from baidupcs_py.baidupcs import BaiduPCSApi, PCS_UA, PcsFile
from baidupcs_py.utils import human_size_to_int
from baidupcs_py.commands.upload import upload as BaiduUpload, DEFAULT_SLICE_SIZE

#def file_rename(src_name):
#    dst_name = src_name.replace(' ', '_')
#    return dst_name

class DownloadParams(SimpleNamespace):
    concurrency: int = 5
    chunk_size: str = str(1 * 1024 * 1024)
    quiet: bool = False

DEFAULT_DOWNLOADPARAMS = DownloadParams()

FromTo = namedtuple("FromTo", ["from_", "to_"])

class BaiduPcsClient():
    def __init__(self, cookies: str, remotedir: str, localdir: str):
        
        self.cookies = dict([c.split("=", 1) for c in cookies.split("; ")])
        self.bduss = self.cookies.get("BDUSS")
        self.api = BaiduPCSApi(bduss=self.bduss, cookies=self.cookies)
        
        self.downloadparams = DEFAULT_DOWNLOADPARAMS
        
        is_file = self.api.is_file(remotedir)
        assert self.api.exists(remotedir), "remotedir must exists"
        assert not is_file, "remotedir must be a directory"
        self.remote_rootdir = remotedir

        self.local_rootdir = localdir
        if not os.path.exists(self.local_rootdir):
            os.makedirs(self.local_rootdir)

    def walk(self, localpath: str) -> Iterator[str]:
        for root, _, files in os.walk(localpath):
            for f in files:
                yield os.path.join(root, f)
    
    def recursive_list(self, remotedir: Union[str, PcsFile]) -> List[PcsFile]:
        '''
        return network pan's file, only file, not include directory
        '''
        if isinstance(remotedir, PcsFile):
            remotedir = remotedir.path
        
        pcs_files = []
        for pcs_file in self.api.list(remotedir):
            if pcs_file.is_dir:
                pcs_files.extend(self.recursive_list(pcs_file.path))
            else:
                pcs_files.append(pcs_file)
        
        return pcs_files


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

    def download_file(self, pcsfile: PcsFile):
        remote_path = pcsfile.path
        dlink = None
        try:
            dlink = self.api.download_link(remote_path)
        except:
            print(f"error: get download link failed for : {remote_path}")
            return None
        
        if not dlink:
            print(f"error: get download link failed for : {remote_path}")
            return None
        
        relative_dir = os.path.relpath(os.path.dirname(remote_path), start=self.remote_rootdir)
        local_dir = os.path.join(self.local_rootdir, relative_dir)
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)
        
        filename = os.path.basename(remote_path)
        local_path = os.path.join(local_dir, filename)
        localpath_tmp = local_path + ".tmp"
        if os.path.exists(localpath_tmp):
            os.remove(localpath_tmp)

        # 判断该文件是否需要下载
        if os.path.exists(local_path):
            file_stat = os.stat(local_path)
            if int(file_stat.st_mtime) != pcsfile.local_mtime \
                or file_stat.st_size != pcsfile.size:
                #print("not need to download {} to {}".format(remote_path, local_path))
                return local_path

        print(f"downloading: {remote_path} to {local_path}")
        cmd = self.aget_py_cmd(url=dlink, localpath=localpath_tmp)
        child = subprocess.run(cmd, stdout=subprocess.DEVNULL if self.downloadparams.quiet else None)
        if child.returncode != 0:
            print(f"{cmd} fails, return code: {child.returncode}")
            print("download failed: {}".format(remote_path))
            os.remove(localpath_tmp)
            return None
        else:
            shutil.move(localpath_tmp, local_path)
            print("download success: {} -> {}".format(remote_path, local_path))
            self.after_file_download(local_path)
            return local_path

    def after_file_download(self, localpath: str):
        file_name = os.path.basename(localpath)
        file_type = get_file_type(localpath)
        
        if FileType.VIDEO == file_type or FileType.AUDIO == file_type:
            with transaction.atomic():
                add_one_video_to_database(
                    full_path=localpath, 
                    repository_path=settings.VIDEO_ROOT, 
                    repository_url=settings.VIDEO_URL, 
                    filename=file_name,
                    keep_files=True
                )


    def download_dir(self,
        remotedir: str,
        recursive: bool = False,
    ):
        remotepaths = self.api.list(remotedir)
        for rp in remotepaths:
            if rp.is_file:
                self.download_file(rp)
            else:  # is_dir
                if recursive:
                    self.download_dir(
                        rp.path,
                        recursive=recursive,
                    )


    def upload_dir(self,
        localdir: str,
        remotedir: str,
    ):
        '''
        将本地新增的文件上传到网盘
        目前只上传FileType.TRANS类型的文件
        '''
        is_file = self.api.is_file(remotedir)
        assert not is_file, "remotedir must be a directory"

        if not self.api.exists(remotedir):
            all_pcs_files = {}
        else:
            all_pcs_files = {
                os.path.relpath(pcs_file.path, start=self.remote_rootdir): pcs_file
                for pcs_file in self.recursive_list(remotedir)
            }

        fts: List[FromTo] = []
        #check_list: List[Tuple[str, PcsFile]] = []
        all_localpaths = set()
        for localpath in self.walk(localdir):
            path = os.path.relpath(localpath, start=self.local_rootdir)
            all_localpaths.add(path)

            if path not in all_pcs_files \
                and FileType.TRANS == get_file_type(localpath):
                fts.append(FromTo(localpath, os.path.join(self.remote_rootdir, path)))
            #else:
            #    check_list.append((localpath, all_pcs_files[path]))

        #for lp, pf in check_list:
        #    lstat = os.stat(lp)
        #    if int(lstat.st_mtime) != pf.local_mtime or lstat.st_size != pf.size:
        #        fts.append(FromTo(lp, pf.path))

        try:
            print("BaiduUpload {}".format(str(fts)))
            BaiduUpload(self.api, fts)
            print("BaiduUpload success")
        except:
            print("BaiduUpload failed")

        #to_deletes = []
        #for rp in all_pcs_files.keys():
        #    if rp not in all_localpaths:
        #        to_deletes.append(all_pcs_files[rp].path)

        #if to_deletes:
        #    self.api.remove(*to_deletes)
        #    print(f"Delete: [i]{len(to_deletes)}[/i] remote paths")


    def sync(self):
        # 1.将视频文件、字幕文件、转写文件从网盘下载到本地
        self.download_dir(self.remote_rootdir, recursive=True)
        # 2.没有字幕的视频尝试获取字幕
        video_set = Video.objects.annotate(subtitles_num=Count('subtitles__video_id')).all()
        for v in video_set:
            if v.subtitles_num == 0: # 没有字幕的视频
                print("try to get subtitles for video named {} ".format(v.name))
                v.get_subtitles(settings.VIDEO_ROOT, settings.VIDEO_URL) 
        # 3.将本地更新的文件上传到网盘备份
        self.upload_dir(self.local_rootdir, self.remote_rootdir)
