#!/bin/env python
#coding:utf-8
#Author:MarineHuang

import argparse,json
import srt
import Levenshtein
import datetime
import chardet
import logging

LOG = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(
        description='''功能: 字幕时间码匹配
        输入1: 语音识别结果，json文件
        输入2: 已经断句的字幕文稿
        输出: 带时间码的字幕文件''',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('-r', '--reg', metavar='识别结果', type=str, required=True, help='语音识别结果的json文件')
    parser.add_argument('-t', '--text', metavar='字幕文稿', type=str, required=True, help='已经断句的字幕文稿')
    parser.add_argument('-o', '--output', metavar='字幕文稿', type=str, required=False, help='输出的字幕文件')

    args = parser.parse_args()

    #force_align(args.reg, args.text, args.output, begin_time=0, end_time=26290, begin_lineno=0, end_lineno=5)
    #force_align(args.reg, args.text, args.output, begin_time=0, end_time=50473, begin_lineno=0, end_lineno=11, Debug=True)
    force_align(args.reg, args.text, args.output, Debug=True)

def print_with_color(words, in_dict):
    '''
    不在dict中的单词用红色打印
    '''
    assert len(words) == len(in_dict), f'length of words must be equal to length of in_dict'
    out_str=""
    for word,in_or_not in zip(words, in_dict):
        if in_or_not:
            out_str += word
        else:
            out_str += f'\033[31m{word}\033[0m'
        out_str += ' '
    LOG.debug(out_str)

def ids2str(ids):
    '''
    将ID转换成unicode码值
    转换方法: chr(id+65)
    为什么是65: 65是字符A的码值，最小的可见字符码值
    '''
    return ''.join(map( lambda x : chr(65+x), ids))

def fa_by_levenshtein(reg_words, txt_words, words_dict, wordpos_line, Debug=False):
    reg_words_id = []
    for word_tupe in reg_words:
        reg_words_id.append(word_tupe['WordID'])
    src_str = ids2str(reg_words_id)
    if Debug:
        LOG.debug(src_str)

    txt_words_id = []
    for word_tupe in txt_words:
        txt_words_id.append(word_tupe['WordID'])
    dest_str = ids2str(txt_words_id)
    if Debug:
        LOG.debug(dest_str)

    # 遍历Levenshtein算法返回的编辑操作
    for op in Levenshtein.opcodes(src_str,dest_str):
        if Debug:
            LOG.debug(op)
        if 'insert' == op[0]:
            # 识别结果中少识别一些单词, 或者说字幕文稿中多了一些单词
            assert  op[2] == op[1], f'insert operation must be at a single position of source sequence'
            reg_word = reg_words[0 if 0 == op[1] else (op[1]-1)]
            for txt_word in txt_words[op[3] : op[4]]:
                txt_word['BeginTime'] = reg_word['BeginTime'] # 字幕文稿中多增加单词分享reg_word中的时间
                txt_word['EndTime'] = reg_word['EndTime']
                txt_word['RegWord'] = f"\033[31m{'*'*len(txt_word['Word'])}\033[0m" # 插入为红色, 用*表示
        elif 'equal' == op[0]:
            assert (op[2] - op[1]) == op[4] - op[3], f'length of sequences which will be operated must be equal'
            for reg_word, txt_word in zip(reg_words[op[1] : op[2]], txt_words[op[3] : op[4]]):
                txt_word['BeginTime'] = reg_word['BeginTime']
                txt_word['EndTime'] = reg_word['EndTime']
                txt_word['RegWord'] = f"\033[32m{reg_word['Word'].strip()}\033[0m" # 相等为绿色
        elif 'replace' == op[0]:
            assert (op[2] - op[1]) == op[4] - op[3], f'length of sequences which will be operated must be equal'
            for reg_word, txt_word in zip(reg_words[op[1] : op[2]], txt_words[op[3] : op[4]]):
                txt_word['BeginTime'] = reg_word['BeginTime']
                txt_word['EndTime'] = reg_word['EndTime']
                txt_word['RegWord'] = f"\033[4;33m({reg_word['Word'].strip()})\033[0m" # 被替换的内容为黄色+下划线
        elif 'delete' == op[0]:
            assert  op[4] == op[3], f'delete operation must be at a single position of destination sequence'
            if 0 == op[3]:
                print(f'delete operation occured at position 0 of destination sequence\n')
            else:
                txt_word = txt_words[op[3] - 1]
                for reg_word in reg_words[op[1] : op[2]]:
                    txt_word['EndTime'] = reg_word['EndTime']
                    txt_word['RegWord'] += f"\033[4;31m {reg_word['Word'].strip()}\033[0m" # 删除为红色+下划线
        else:
            LOG.error(f'error: invalid operation named {op[0]}')

    subtitle_list=[]

    for (lineno, wordpos) in wordpos_line.items():
        beg=wordpos['beg_wordpos']
        end=wordpos['end_wordpos']
        tmp_txt=[]
        tmp_reg=[]
        beg_time=txt_words[beg]['BeginTime']
        end_time=beg_time
        for word_tupe in txt_words[beg : end]:
            tmp_txt.append(word_tupe['Word'])
            tmp_reg.append(word_tupe['RegWord'])
            end_time = word_tupe['EndTime']
        
        # construct subtitle
        srt_beg_time = datetime.timedelta(seconds=(beg_time // 1000), microseconds=(beg_time % 1000 * 1000))
        srt_end_time = datetime.timedelta(seconds=(end_time // 1000), microseconds=(end_time % 1000 * 1000))

        if Debug:
            LOG.debug(' '.join(tmp_txt))
            LOG.debug(' '.join(tmp_reg))
            #LOG.debug(beg_time)
            #LOG.debug(end_time)
        
        #beg_time, end_time的单位为毫秒
        subtitle_list.append(
            srt.Subtitle(index=0, start=srt_beg_time, end=srt_end_time, content=' '.join(tmp_txt))
        )

    return subtitle_list

def force_align(reg_result, text, out_file, begin_time=0, end_time=None, 
    begin_lineno=0, end_lineno=None, Debug=False):
    '''
    字幕时间码匹配
    Args:
        reg_result: 语音识别结果，dict or str(means file path)
        text: 断好句的字幕文本文件, list of str or str(means file path)
        out_file: 输出的字幕文件
    Return:
        list of srt.Subtitle
    '''
    if 'end_time' not in vars():
        end_time = None
    if 'end_lineno' not in vars():
        end_lineno = None

    words_list=[]
    txt_list=[]

    if isinstance(reg_result, dict):
        words_list = reg_result['Result']['Words']
    elif isinstance(reg_result, str):
        encoding='utf-8'
        with open(reg_result, "rb") as fp:
            encoding = chardet.detect(fp.read())["encoding"]
        with open(reg_result, 'r', encoding=encoding) as freg:
            json_reg = json.load(freg)
            words_list = json_reg['Result']['Words']
    else:
        raise Exception(f'invalid type of parameter \"reg_result\" which must be \
dict or str(means file path) and really is {type(reg_result)}')
        
    begin_index = 0
    for i,word in enumerate(words_list):
        if word['BeginTime'] > begin_time:
            begin_index = i
            break

    end_index = len(words_list)
    if None is not end_time:
        for i,word in enumerate(words_list, start=begin_index):
            if word['BeginTime'] > end_time:
                end_index = i + begin_index
                break

    words_list = words_list[begin_index : end_index]
    #if Debug:
    #    LOG.debug(words_list)

    if isinstance(text, list):
        txt_list = text
    elif isinstance(text, str):
        encoding='utf-8'
        with open(text, "rb") as fp:
            encoding = chardet.detect(fp.read())["encoding"]
        with open(text, 'r', encoding=encoding) as ftxt:
            txt_list = ftxt.readlines()
    else:
        raise Exception(f'invalid type of parameter \"text\" which must be \
list of str or str(means file path) and really is {type(text)}')

    if None is end_lineno:
        end_lineno = len(txt_list)
    txt_list = txt_list[begin_lineno : end_lineno]
    #if Debug:
    #    print(txt_list)

    # 将识别结果word放入dict中，并转换成WordID
    words_dict={}
    for word_tupe in words_list:
        word = word_tupe['Word']
        word = word.strip().lower()
        if word in words_dict.keys():
            word_tupe['WordID'] = words_dict[word]
        else:
            words_dict[word] = len(words_dict.keys())
            word_tupe['WordID'] = words_dict[word]

    # 检查txt_list中单词是否在识别结果中
    txt_words=[]
    wordpos_line={}
    for lineno,line in enumerate(txt_list):
        wordpos_line[lineno] = {'beg_wordpos': len(txt_words)}
        line = line.strip()
        words = line.split()
        in_dict = [1]*len(words)
        for i,word in enumerate(words):
            word_tupe = {}
            word_tupe['Word'] = word
            word = word.strip().lower() # 小写
            word = word.rstrip(',.') # 删除结尾处的，和.
            if word not in words_dict.keys():
                in_dict[i] = 0
                words_dict[word] = len(words_dict.keys()) #将不在识别结果中的单词放入words_dict中
            word_tupe['WordID'] = words_dict[word]
            word_tupe['LineNo'] = lineno
            word_tupe['WordPos'] = i
            txt_words.append(word_tupe)
        wordpos_line[lineno]['end_wordpos'] = len(txt_words)
        #打印出不在words_dict的单词
        if Debug:
            #LOG.debug(txt_words)
            #LOG.debug(wordpos_line)
            print_with_color(words, in_dict)

    # 使用Levenshtein进行对齐
    subtitle_list = fa_by_levenshtein(words_list, txt_words, words_dict, wordpos_line, Debug)
    
    with open(out_file, 'w', encoding='utf-8') as f:
        content = srt.compose(subtitle_list, reindex=True, start_index=1, strict=True)
        f.write(content)
    
    return subtitle_list

if __name__ == '__main__':
    main()
