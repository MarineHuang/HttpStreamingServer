# -*- coding: utf-8 -*-
import os, subprocess, time, json, datetime, re
from urllib import response
import traceback

from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest


class AliTrans():
    def __init__(self, app_key, access_key_id, access_key_secret, name):
        self.appKey = app_key
        # 地域ID，常量内容，请勿改变
        self.REGION_ID = "cn-shanghai"
        self.PRODUCT = "nls-filetrans"
        self.DOMAIN = "filetrans.cn-shanghai.aliyuncs.com"
        self.API_VERSION = "2018-08-17"
        self.description = name
        
        # 创建AcsClient实例
        self.client = AcsClient(access_key_id, access_key_secret, self.REGION_ID)
    
    def __str__(self):
        return self.description

    def submit_task(self, audio_url):
        # 提交录音文件识别请求
        postRequest = CommonRequest()
        postRequest.set_domain(self.DOMAIN)
        postRequest.set_version(self.API_VERSION)
        postRequest.set_product(self.PRODUCT)
        postRequest.set_action_name('SubmitTask')
        postRequest.set_method('POST')
        # 新接入请使用4.0版本，已接入(默认2.0)如需维持现状，请注释掉该参数设置
        # 设置是否输出词信息，默认为false，开启时需要设置version为4.0
        task = {
            "appkey": self.appKey,
            "file_link": audio_url,
            "version": "4.0",
            "enable_words": True,
            "max_single_segment_time": 10000,
            #"auto_split": True, # 是否开启智能分轨
        }
        # print(json.dumps(task))
        postRequest.add_body_params('Task', json.dumps(task))
        
        task_id=None
        try:
            response_data = self.client.do_action_with_exception(postRequest)
            #response_data = '{"TaskId": "010b254000b911ec894541fc5c7130b6", "RequestId": "CFF53121-E7B4-50B1-82A3-F297E378BBAC", "StatusText": "SUCCESS", "StatusCode": 21050000}'
            response = json.loads(response_data)
            print(f'response: {response}')

            status_text = response['StatusText']

            if status_text == "SUCCESS":
                task_id = response['TaskId']
                print(f'submit transcription task suceess, status_text: {status_text}, task_id: {task_id}')
                return True
            elif status_text == 'USER_BIZDURATION_QUOTA_EXCEED':
                print(f'你今天的阿里云识别额度已用完, status_text: {status_text}')
                return False
            else:
                print(
                    f'录音文件识别请求失败，失败原因是: {status_text}，你可以将这个代码复制，到 “https://help.aliyun.com/document_detail/90727.html” 查询具体原因')
                return False
        except Exception as ex:
            print(f'error when submit transcription task: {ex}')
            traceback.print_exception(type(ex), ex, ex.__traceback__)
            return False
        finally:
            return task_id

    def query_task(self, task_id):
        # 创建CommonRequest
        request = CommonRequest()
        request.set_domain(self.DOMAIN)
        request.set_version(self.API_VERSION)
        request.set_product(self.PRODUCT)
        request.set_action_name('GetTaskResult')
        request.set_method('GET')
        request.add_query_param('TaskId', task_id)
        # 提交录音文件识别结果查询请求
        # 以轮询的方式进行识别结果的查询，直到服务端返回的状态描述符为"SUCCESS"、"SUCCESS_WITH_NO_VALID_FRAGMENT"，
        # 或者为错误描述，则结束轮询。
        status="FAILD"
        reg_result=None
        try:
            response_data = self.client.do_action_with_exception(request)
            # 识别结果json
            response = json.loads(response_data)
            print(f'response of transcription result: {response}')
            status = response['StatusText']
            if status == "SUCCESS":
                print(f'task named {task_id} success')
                reg_result = response
            elif status == "QUEUEING":
                print(f'task named {task_id} QUEUEING')
            elif status == "RUNNING":
                print(f'task named {task_id} RUNNING')
            else:
                print(f'unknown status of task named {task_id}: {status}')
        except Exception as ex:
            print(f'error occours when query task named {task_id}: {ex}')
            traceback.print_exception(type(ex), ex, ex.__traceback__)
            status="FAILD"
        finally:
            return (status, reg_result)

