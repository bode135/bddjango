"""
纯python的功能函数
"""
import json
import pandas as pd
import inspect
import functools
import os
import threading
import shutil
from bdtime import Time
import datetime as dt


TEMPDIR = 'tempdir'     # 临时文件夹


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


def get_class_that_defined_method(meth):
    """
    get mehod's class
    """
    if isinstance(meth, functools.partial):
        return get_class_that_defined_method(meth.func)
    if inspect.ismethod(meth) or (inspect.isbuiltin(meth) and getattr(meth, '__self__', None) is not None and getattr(meth.__self__, '__class__', None)):
        for cls in inspect.getmro(meth.__self__.__class__):
            if meth.__name__ in cls.__dict__:
                return cls
        meth = getattr(meth, '__func__', meth)  # fallback to __qualname__ parsing
    if inspect.isfunction(meth):
        cls = getattr(inspect.getmodule(meth),
                      meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0],
                      None)
        if isinstance(cls, type):
            return cls
    return getattr(meth, '__objclass__', None)  # handle special descriptor objects


def get_whole_codename_by_obj_and_perm(obj=None, perm=None, suffix_model_name=False):
    """
    得到obj的perm对应的完整codename: whole_codename

    - eg:
    ```
    perm = get_whole_codename_by_obj_and_perm(obj=model, perm=perm_codename, suffix_model_name=ssuffix_model_name)
    ret = user.has_perm(perm)
    ```

    :param obj: 模型 or 对象
    :param perm: 权限名
    :param suffix_model_name: perm里边没有obj对应model的model_name, 需要函数手动添加
    :return:
    """
    if obj:
        if suffix_model_name:
            ret = f'{obj._meta.app_label}.{perm}_{obj._meta.model_name}'
        else:
            ret = f'{obj._meta.app_label}.{perm}'
    else:
        ret = perm
    return ret


def conv_df_to_serializer_data(df) -> list:
    assert isinstance(df, pd.DataFrame), 'df的类型必须是DataFrame!'
    ret_ls = []
    for index, row in df.iterrows():
        k = row.index.tolist()
        v = row.values.tolist()
        data = dict(zip(k, v))

        ret_ls.append(data)
    return ret_ls


def convert_query_parameter_to_bool(query_parameter, false_ls=None):
    """
    将请求参数转化为`bool`类型

    :param query_parameter: 请求参数
    :param false_ls: 将转换为`false`的值
    :return: bool, true or false
    """
    if false_ls is None:
        false_ls = ['0', 0, None, 'None', 'Null', [], [''], {}, 'False', 'false', '', 'null']
    ret = query_parameter not in false_ls
    return ret


def _remove_temp_file(tempdir=TEMPDIR, MAX_TEMPS=5, desc='---', remain_rows=None, option_model='getatime', quiet=False):
    """
    清理缓存, 清空tempdir下的所有文件
    :param tempdir: 文件路径
    :param MAX_TEMPS: 最多缓存文件数量
    :param remain_rows: 最清理时留下的缓存文件数量, 如空, 则保留1/3
    :param option_model: 操作模式, os.path的[getatime, getctime, getmtime]函数

    # :param MAX_SPACE: 最大缓存文件空间
    """
    fpath_ls = os.listdir(tempdir)
    temps = len(fpath_ls)

    if temps < MAX_TEMPS:
        if not quiet:
            print(f'...缓存还足够, 不用清理... 缓存容量: {temps}/{MAX_TEMPS}')
        return False

    # --- 按option_model选择的时间函数来清理缓存文件
    if option_model in ['getatime', 'getctime', 'getmtime']:        # remain_recent
        # print(option_model)
        col_0 = 'filename'
        fpath_df = pd.DataFrame(fpath_ls, columns=[col_0])
        f = getattr(os.path, option_model)
        fpath_df['abs_fpath'] = [os.path.join(tempdir, f_i) for f_i in fpath_df[col_0]]
        fpath_df['t_tamp_ls'] = [f(os.path.join(tempdir, f_i)) for f_i in fpath_df[col_0]]
        fpath_df['t_str_ls'] = [dt.datetime.fromtimestamp(f_i).strftime("%Y-%m-%d %H:%M:%S") for f_i in fpath_df['t_tamp_ls']]

        # 删到remain_rows个文件为止
        remain_rows = remain_rows if remain_rows else MAX_TEMPS//3
        delete_rows = temps - remain_rows

        # delete_fpath_df[['t_tamp_ls', 't_str_ls']]
        delete_fpath_df = fpath_df.sort_values(by='t_tamp_ls')[:delete_rows]

        # --- 按空间清理
        # remain_fpath_df = fpath_df.sort_values(by='t_tamp_ls', ascending=False)[:MAX_TEMPS]
        # remain_fpath_df['size'] = [os.path.getsize(os.path.join(tempdir, f_i)) for f_i in remain_fpath_df[col_0]]
        #
        # remain_fpath_df[['t_str_ls', 'size']]
        # # MAX_SPACE = 1024 * 10
        #
        # s = 0
        # size_ls = fpath_df['size'].tolist()
        # size_ls.reverse()
        # for i in range(fpath_df.shape[0]):
        #     size = size_ls[i]
        #     s += size
        #     print(i, size, s)
        #     if s >= MAX_SPACE:
        #         break
        # space_i = i - 1
        # space_i
        # fpath_df.sort_values(by='size')[:MAX_TEMPS]

        fpath_ls = delete_fpath_df[col_0].tolist()
        temps = len(fpath_ls)

    tt = Time()

    tt.sleep(1)
    if not quiet:
        print(f'*************** 开始清理缓存 {tempdir} *************')
    for fpath in fpath_ls:
        i = 0
        tt.__init__()
        while tt.during(5):
            i += 1
            dirpath = os.path.join(tempdir, fpath)

            try:
                if os.path.isdir(dirpath):
                    # os.removedirs(dirpath)
                    shutil.rmtree(dirpath)
                else:
                    os.remove(dirpath)
                if not quiet:
                    print(f"~~~ success: 移除文件[{dirpath}]成功! -- 第[{i}]次")
                break
            except:
                print(f"** 第[{i}]次移除文件[{dirpath}]失败...可能文件被占用中?")
                tt.sleep(1)
                if i > 3:
                    print(f"======== Warning: 移除文件[{dirpath}]失败!")
    if not quiet:
        print(f'*************** [{desc}] 缓存清理完毕 *************')
    return True


def remove_temp_file(tempdir=TEMPDIR, MAX_TEMPS=5, desc='---', remain_rows=None, option_model='getatime', quiet=True):
    """
    当大于MAX_TEMPS时启动临时文件清理程序
    """
    temps = len(os.listdir(tempdir))

    if temps > MAX_TEMPS:
        t1 = threading.Thread(target=_remove_temp_file, args=(tempdir, MAX_TEMPS, desc, remain_rows, option_model, quiet))
        t1.start()
        return True
    else:
        if not quiet:
            print(f'{desc} --- 缓存还足够, 不用清理... 缓存文件: {temps}/{MAX_TEMPS}, tempdir: {tempdir}')
        return False


class SetUtils:
    @staticmethod
    def get_ls_a_and_b(ls_a, ls_b):
        # 获得列表a和b的交集 a and b
        ret = [j for j in ls_a if j in ls_b]
        return ret

    @staticmethod
    def get_ls_a_or_b(ls_a, ls_b):
        # 获得列表a和b的交集 a and b
        ret = list(set(ls_a) | (set(ls_b)))
        return ret

    @staticmethod
    def get_ls_a_different_ls_b(a, b, keep_sort=True):
        """
        列表a和列表b的差集a-b, 并保留a列表原顺序
        """
        ret = list(set(a) - set(b))
        if keep_sort:
            ret.sort(key=a.index)
        return ret

    get_ls_a_sub_b = get_ls_a_different_ls_b


set_utils = SetUtils()

