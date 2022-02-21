"""
纯python的功能函数
"""
import json
import os
import pandas as pd


def version():
    """
    * 2021/2/21

    # 党史项目结束, 海南项目开始

    ## 修改部分
        - 修复了AdvancedSearchView post时page_size失效的问题
        - 对`list`的数据返回格式进行了优化, 避免了自定义page_size时无效的bug
        - `BaseListView`增加`set_request_data`方法
        - 优化`distince_type_ls`和o`rder_type_ls`的错误提示
        - `AdvancedSearchView`增加`Q_add_ls`检索方法
        - `.pure`增加`convert_query_parameter_to_bool`函数
        - '.django'增加`update_none_to_zero_by_field_name`函数
        - 增加`AliasField`绑定字段方法
        - 按年份分布的统计方法`get_df_by_freq_and_year`
        - 修复distinct_field_ls和order_type_ls的冲突
    """
    v = "2.1.4"     # 正式版: 2.1.3
    return v


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


import inspect
import functools


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
    if not false_ls:
        false_ls = ['0', 0, None, 'None', 'Null', [], {}, 'False', 'false', '', 'null']
    ret = query_parameter not in false_ls
    return ret

