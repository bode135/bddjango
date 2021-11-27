#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
杀死占用指定端口号的进程, 跨平台通用版本(mac和win).

使用示例:
    python kill_port.py 8000
"""


import sys, os, platform
import re


# Mac
def mac_kill_port(port):
    ret = None
    # 查找端口的pid
    find_port = f'ps -ef|grep {port}'
    print(f'~~~ find_port: {find_port} \n')

    result = os.popen(find_port)
    text = result.read()

    print(text)
    # 匹配所有的pid
    reg = re.compile(r'^.*? (\d+) .*? (.*?)$', re.M)
    res = reg.findall(text)
    # print(res)

    # 杀死所有进程
    k = 0
    for pid, tag in res:
        if 'killtask' not in tag and 'ps -ef' not in tag and 'grep' not in tag and len(pid) > 3:
            find_kill = f'kill -9 {pid}'
            print('------ killed pid:', pid)
            result = os.popen(find_kill)
            ret = result.read()
            k += 1
        else:
            print('*** passed pid:', pid, "|tag: ", tag)

    if k == 0:
        print(f'\n ****** 没有找到占用[{port}]的程序. ******')
    else:
        print(f'\n------ 成功杀死占用[{port}]的{k}个程序! ----------')
    return ret


# Win版本
def win_kill_port(port):
    # 查找端口的pid

    find_kill = "taskkill /f /im {port}"
    print('---- taskkill命令:', find_kill)
    result = os.popen(find_kill)

    print(f'***** 成功清理了[{port}]. *****')
    return result.read()


if __name__ == '__main__':
    # 使用方法: python kill_port.py [to_be_killed_port]

    # 判断平台
    if platform.system() == "Windows":
        kill_port = win_kill_port
    else:
        kill_port = mac_kill_port

    print(f'***** 系统变量名: {sys.argv}\n')
    if sys.argv.__len__() == 1:
        # 如果没有带参数, 就默认杀掉8000端口
        port = 8000
    else:
        port = sys.argv[1]
    kill_port(port)
