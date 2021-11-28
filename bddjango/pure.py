"""
纯python的功能函数
"""
import json
import os


def version():
    return '1.4.2'


def add_status_and_msg(dc_ls, status=200, msg=None):
    if status != 200 and msg is None:
        msg = '请求数据失败!'

    if status == 200 and msg is None:
        msg = "ok"

    ret = {
        'status': status,
        'msg': msg,
        'result': dc_ls
    }
    return ret


def show_json(data: dict, sort_keys=False):
    try:
        print(json.dumps(data, sort_keys=sort_keys, indent=4, separators=(', ', ': '), ensure_ascii=False))
    except:
        if isinstance(data, dict):
            for k, v in data.items():
                print(k, ' --- ', v)
        else:
            for k, v in data:
                print(k, ' --- ', v)


def show_ls(data: list, ks=None):
    for dc in data:
        if ks:
            if isinstance(ks, str):
                ks = [ks]
            d = [dc.get(k) for k in ks]
        else:
            d = dc
        print(d)


def add_space_prefix(text, n, more=True, prefix='\u3000'):
    text = str(text)
    if more:
        ret = prefix * n + text
    else:
        ret = prefix * (n - len(text)) + text
    return ret


def create_file_if_not_exist(file_name):
    if not os.path.exists(file_name):
        with open(file_name, 'w') as f:
            f.write('')
        return False
    return True


def create_dir_if_not_exist(dirpath: str):
    if not os.path.exists(dirpath):
        os.mkdir(dirpath)
        return False
    return True
