#coding=utf-8

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
    find_port = f'lsof -i tcp:{port}'
    print(f'~~~ find_port: {find_port} \n')

    result = os.popen(find_port)
    text = result.read()
    print(text)

    # 匹配所有的pid
    reg = re.compile(r'\n.*? (\d+) ')
    res = reg.findall(text)

    # 杀死所有进程
    for pid in res:
        # 占用端口的pid
        find_kill= f'kill -9 {pid}'
        print('--- find_kill: ', find_kill)
        result = os.popen(find_kill)
        ret = result.read()

    if ret is None:
        print(f'\n ----- 没有找到占用[{port}]的端口. ----------')
    else:
        print(f'\n------ 成功杀死占用[{port}]的端口! ----------')
    return ret


# Win版本
def win_kill_port(port):
    # 查找端口的pid
    # netstat -aon | findstr "8000"
    find_port= 'netstat -aon | findstr %s' % port
    print('---- find_port命令:', find_port)

    result = os.popen(find_port)
    text: str = result.read()

    reg = re.compile(r' (\S+)\n')
    pids = reg.findall(text)

    print(f"-------------- find_port: [{find_port}] ---------------")
    for ss in text.split('\n'):    print(ss)
    print(f'       ---- pids: {pids} ----')
    print()

    def kill_one_process(pid):
        if not pid:
            print(f"\n****** 没有发现[{port}]端口被占用! *******")
            return 0

        # 占用端口的pid
        print(f'----- 占用端口的pid: {pid}')
        find_kill = 'taskkill -f -pid %s' % pid
        print('---- find_kill命令:', find_kill)
        result = os.popen(find_kill)

    for pid in pids:
        try:
            kill_one_process(pid)
        except Exception as e:
            print(e)

    print(f'***** 成功清理了[{port}]端口. *****')
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
