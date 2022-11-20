#!/bin/env python
#coding:utf-8
#Author:MarineHuang
import os
import datetime
import traceback
import time
import tempfile
import json
#from datetime import timedelta
#from celery import shared_task
#from celery.schedules import crontab, schedule
#from redbeat import RedBeatSchedulerEntry

from AIServiceApp.models import SpeechRecognizer
from AIServiceApp.ali import AliTrans, AliOss
from StreamServerApp.media_management.processing import transfor_audio
#from StreamingServer.celery import celery_app

#from .subtitle_aligner import force_align
#
#def trans_audio_file_callback(transcript_result):
#    print("start subtitle force align")
#    force_align(
#        reg_file="/usr/torrent/obama10m.reg",
#        text_file="/usr/torrent/obama10m.txt",
#        out_file="/usr/torrent/obama10m.srt" 
#    )

def create_trans_client():
    trans_client = None
    oss_client = None
    queryset = SpeechRecognizer.objects.all()
    for sr in queryset:
        try:
            trans_client = AliTrans(sr.app_key, 
                sr.access_key_id, 
                sr.access_key_secret, 
                sr.name)
            oss_client = AliOss(sr.oss_bucket_name, 
                sr.oss_endpoint_domain, 
                sr.oss_access_key_id, 
                sr.access_key_secret)
        except Exception as ex:
            print(f'error occours when create transcription and oss client: {ex}')
            traceback.print_exception(type(ex), ex, ex.__traceback__)
        finally:
            if trans_client and oss_client:
                print("create trancription and oss client success")
                #break
            else:
                #continue
                pass
    
    return (trans_client, oss_client)
'''
@shared_task
def query_transcription_result(task_id):
    def delete_task_scheduler():
        # 通过key，删除任务
        key = f'redbeat:{task_id}'   # 配置中的redbeat_key_prefix + task_name
        entry = RedBeatSchedulerEntry.from_key(key, app=celery_app)
        entry.delete()
        print(f"periodic task for querying transcription result {task_id} ended")

    print("query transcription task named {}".format(task_id))
    trans_client, oss_client = create_trans_client()
    status, reg_result = trans_client.query_task(task_id)
    if status == "SUCCESS":
        delete_task_scheduler()
        print(f'task named {task_id} success')
        print(f"transcription result: {reg_result}")
        trans_audio_file_callback(reg_result)
    elif status == "QUEUEING":
        print(f'task named {task_id} QUEUEING')
    elif status == "RUNNING":
        print(f'task named {task_id} RUNNING')
    else:
        print(f'task named {task_id} failed')
        delete_task_scheduler()
'''
def transcript_media_file(media_file_path: str) -> dict:
    if not os.path.exists(media_file_path):
        print(f"{media_file_path} not exists")
        return None

    trans_client, oss_client = create_trans_client()
    if not (trans_client and oss_client):
        print("There is not a vlid trancription and oss client.")
        return None
    
    with tempfile.TemporaryDirectory() as tmpdir:
        media_filename = os.path.splitext(os.path.basename(media_file_path))[0]
        audio_path = os.path.join(tmpdir, media_filename+'.wav')

        transfor_audio(media_file_path, audio_path)

        # upload auido file to oss 
        file_name = os.path.basename(audio_path)
        dest_path = os.path.join(
            #datetime.datetime.now().strftime('%Y-%m-%d'),
            'audio',
            file_name
        )
        audio_remote_url = oss_client.upload(audio_path, dest_path)
        print("upload {} to {}".format(audio_path, audio_remote_url))

    # submit transcription task
    task_id = trans_client.submit_task(audio_remote_url)
    if task_id:
        print("submit transcription task success, lcoal path: {}, engine: {}, task id: {}".format(
            media_file_path, str(trans_client), task_id))
        
        #entry = RedBeatSchedulerEntry(
        #    name = task_id, 
        #    task = 'AIServiceApp.transcription.query_transcription_result', 
        #    schedule = schedule(timedelta(seconds=5)), 
        #    kwargs = {
        #        "task_id": task_id,
        #    }, 
        #    app=celery_app
        #)
        #key = entry.key
        #print(f"the key of periodic task for querying transcription result is {key}")
        #entry.save()
        while True:
            task_status, task_result = trans_client.query_task(task_id)
            if task_status == "SUCCESS":
                print(f'transcription task named {task_id} success')
                #print(f"transcription result: {task_result}")
                return task_result
            elif task_status == "QUEUEING":
                print(f'transcription task named {task_id} queueing')
                time.sleep(20)
            elif task_status == "RUNNING":
                print(f'transcription task named {task_id} running')
                time.sleep(10)
            else:
                print(f'transcription task named {task_id} failed: {task_status}')
                return None

    else:
        print("submit transcription task failed, lcoal path: {}, engine: {}".format(
            media_file_path, str(trans_client)))
        return None
