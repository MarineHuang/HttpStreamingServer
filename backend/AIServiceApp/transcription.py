#!/bin/env python
#coding:utf-8
#Author:MarineHuang
import os
import datetime
import traceback
import time
import tempfile
import json
from AIServiceApp.models import SpeechRecognizer
from AIServiceApp.ali import AliTrans, AliOss
from StreamServerApp.media_management.processing import transfor_audio


def create_trans_client():
    trans_client = None
    oss_client = None
    queryset = SpeechRecognizer.objects.all()
    for sr in queryset:
        try:
            trans_client = AliTrans(sr.app_key, 
                sr.access_key_id, 
                sr.access_key_secret, 
                sr.name
            )
            
            oss_client = AliOss(sr.oss_bucket_name, 
                sr.oss_endpoint_domain, 
                sr.oss_access_key_id, 
                sr.access_key_secret
            )
        except Exception as ex:
            print(f'error occours when create transcript and oss client: {ex}')
            traceback.print_exception(type(ex), ex, ex.__traceback__)
        finally:
            if trans_client and oss_client:
                print("create transcript and oss client success")
            else:
                pass
    
    return (trans_client, oss_client)

def transcript_media_file(media_file_path: str) -> dict:
    if not os.path.exists(media_file_path):
        print(f"{media_file_path} not exists")
        return None

    trans_client, oss_client = create_trans_client()
    if not (trans_client and oss_client):
        print("There is not a vlid transcript and oss client.")
        return None
    
    with tempfile.TemporaryDirectory() as tmpdir:
        media_filename = os.path.splitext(os.path.basename(media_file_path))[0]
        audio_path = os.path.join(tmpdir, media_filename+'.wav')

        transfor_audio(media_file_path, audio_path)

        # upload auido file to oss 
        file_name = os.path.basename(audio_path)
        dest_path = os.path.join(
            'audio',
            file_name
        )
        audio_remote_url = oss_client.upload(audio_path, dest_path)
        print("upload {} to {}".format(audio_path, audio_remote_url))

    # submit transcription task
    task_id = trans_client.submit_task(audio_remote_url)
    if task_id:
        print("submit transcript task success, lcoal path: {}, \
engine: {}, task id: {}".format(media_file_path, str(trans_client), task_id))
        
        while True:
            task_status, task_result = trans_client.query_task(task_id)
            if task_status == "SUCCESS":
                print(f'transcript task named {task_id} success')
                #print(f"transcription result: {task_result}")
                return task_result
            elif task_status == "QUEUEING":
                print(f'transcript task named {task_id} queueing')
                time.sleep(20)
            elif task_status == "RUNNING":
                print(f'transcript task named {task_id} running')
                time.sleep(10)
            else:
                print(f'transcript task named {task_id} failed: {task_status}')
                return None

    else:
        print("submit transcript task failed, lcoal path: {}, \
engine: {}".format(media_file_path, str(trans_client)))
        return None
