import os
import threading
import shutil
from bdtime import Time
import pandas as pd
import datetime as dt


def remove_path(path, keep_external_folder=False):
    if not os.path.exists(path):
        return

    if os.path.isfile(path):
        os.remove(path)
    else:
        assert path not in ['/'], '非法目标路径!'
        shutil.rmtree(path)
        if keep_external_folder:
            os.makedirs(path, exist_ok=True)


def remove_temp_file(tempdir, max_temps=100, remain_rows=0.33, keep_external_folder=False, desc='---',
                     option_model='getctime', quiet=False):
    """
    # 清理临时文件夹

    - option_model取值:
        - os.path.getatime() 函数是获取文件最后访问时间
        - os.path.getmtime() 函数是获取文件最后修改时间
        - os.path.getctime() 函数是获取文件最后创建时间

    :param tempdir: 目标临时文件夹
    :param max_temps: 最大临时文件数量
    :param remain_rows: 清理后保留多少文件(按创建时间删除旧的临时文件). 小于1则按百分比保留, 等于0则清理全部缓存文件
    :param keep_external_folder: `remain_rows`为0时, 是否保留文件夹
    :param desc: 描述信息
    :param quiet: 静默运行
    :param option_model: 删除旧文件时的排序方式
    :return:
    """
    assert os.path.exists(tempdir), f'tempdir: `{tempdir}`不存在!'
    assert remain_rows >= 0, 'remain_rows必须大于等于0!'

    if remain_rows == 0:
        remove_path(tempdir, keep_external_folder=keep_external_folder)
        return 1

    dir_list = os.listdir(tempdir)

    length = len(dir_list)
    if length > max_temps:

        if remain_rows < 1:
            remain_rows = length * remain_rows

        remain_rows = int(remain_rows)

        try:
            f = getattr(os.path, option_model)
        except Exception as e:
            raise AttributeError(f'os.path没有属性`{option_model}`! error: {e}')

        dir_list = sorted(dir_list, key=lambda x: f(os.path.join(tempdir, x)))
        for i in range(length - remain_rows):
            _temp_file = os.path.join(tempdir, dir_list[i])
            remove_path(_temp_file)

        os.makedirs(tempdir, exist_ok=True)

        if not quiet:
            print(desc)

    return 1


