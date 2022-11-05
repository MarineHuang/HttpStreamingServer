# -*- coding: utf-8 -*-
"""
network storage utilies module, provide method for syncronizing
videos with network storage

"""
import os

from baidupcs_py.baidupcs import BaiduPCSApi
from baidupcs_py.commands.download import download_file, Downloader, DownloadParams
#from baidupcs_py.commands.list_files import list_files as BaiduListFiles

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





        
