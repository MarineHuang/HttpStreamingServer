#!/usr/bin/env python
# -*- coding: utf-8 -*-
 
import hashlib
import chardet
import os
 
def get_file_md5(filepath):
    """
    计算文件的md5
    :param filepath:
    :return:
    """
    m = hashlib.md5()   #创建md5对象
    with open(filepath,'rb') as fobj:
        while True:
            data = fobj.read(4096)
            if not data:
                break
            m.update(data)  #更新md5对象
 
    return m.hexdigest()    #返回md5对象
 
 
def get_str_md5(content):
    """
    计算字符串md5
    :param content:
    :return:
    """
    m = hashlib.md5(content) #创建md5对象
    return m.hexdigest()

language_map={
    'Chinese' : 'chi',
    'English' : 'eng',
    'Japanese': 'jap',
    'Russian' : 'rua',
}

def get_file_language(filepath):
    '''
    探测文件的语种
    '''
    language = None
    with open(filepath, "rb") as fp:
        language = chardet.detect(fp.read())["language"]
    
    if language in language_map.keys():
        return language_map[language]
    else:
        return 'unk'

language_filenames = {
    'chi': ['cn', 'chi', 'zh-cn', '中文' ],
    'eng': ['en', 'eng', 'english', '英文' ],
}

def get_file_language_byname(filepath):
    '''
    通过文件名获取文件的语种
    '''
    filename = os.path.basename(filepath)
    filename_list = filename.lower().split('.')
    for lang, lang_filenames in language_filenames.items():
        for lang_filename in lang_filenames:
            if lang_filename in filename_list:
                return lang

    return 'unk'
