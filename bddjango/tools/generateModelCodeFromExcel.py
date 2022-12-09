"""
# 指定excel/csv数据文件, 自动生成django模型代码

## 安装
pip install pandas
pip install pypinyin

## 使用
python tools\generateModelCodeFromExcel.py -f search\docs\测试表.xls

## 打包
pyinstaller -i exe.ico -F generateModelCodeFromExcel.py
pyinstaller -i exe.ico -D generateModelCodeFromExcel.py

"""

import pandas as pd
import os
from pypinyin import lazy_pinyin
import re
from warnings import warn
import sys
from time import sleep


# region # --- cmd参数
import argparse


def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return 1
    elif val in ('n', 'no', 'f', 'false', 'off', '0', 'none', 'null'):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))


def parse_args():
    """
    # 参数解释

    # 其它类型参数:
    parser.add_argument("--seed", type=int, default=1,
                        help="seed of the experiment")
    parser.add_argument("--float", type=float, default=1.2345,
                        help="float")
    parser.add_argument('-ls', '-list', action='append')      # 输入列表
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', "--f-path", type=str,
                        help="要生成model代码的excel数据文件路径")
    parser.add_argument('-m', "--model-name", type=str,
                        help="指定model_name")
    parser.add_argument(
        '-a', "--add-db-column", type=lambda x: bool(strtobool(x)), default=False, nargs="?", const=True,
        help="如果选中, 则加上db_column参数."
    )

    args = parser.parse_args()
    return args
# endregion


# region # --- 核心代码
ADD_DB_COLUMN = False


def replace_string(old_string, string, start, end):
    """
    字符串按索引位置替换字符
    """
    old_string = str(old_string)
    # 新的字符串 = 老字符串[:要替换的索引位置] + 替换成的目标字符 + 老字符串[要替换的索引位置+1:]
    new_string = old_string[:start] + string + old_string[end:]
    return new_string


def auto_generate_model_field_name(column_name):
    """
    转为驼峰命名
    """
    reg = re.compile(r'[\u4e00-\u9fa5]')
    match = reg.search(column_name)  # 判断是否有汉字

    if match:
        ret = '_'.join(lazy_pinyin(column_name))
    else:
        ret = column_name
    ret = ret.replace(' ', '_').lower()
    ret = re.sub('_+', '_', ret)  # 不能有两个以上的连续空格
    return ret


def get_model_info(f_path=None, model_name=None, add_db_column=None, columns=None, rename_file_name=None):
    """
    # 获取模型信息

    - f_path: 原始文件名
    - add_db_column: 是否增加`db_column`字段
    - rename_file_name: 重命名文件名
    """

    if f_path:
        format_ls = ['.csv', '.xls', '.xlsx']
        f_format = os.path.splitext(f_path)[-1]
        my_exe_assert_function(f_format in format_ls, f'Error! 仅支持 {format_ls} 类型的文件!')

        add_db_column = add_db_column if add_db_column else ADD_DB_COLUMN
        if f_format != '.csv':
            df_0: pd.DataFrame = pd.read_excel(f_path)
        else:
            df_0: pd.DataFrame = pd.read_csv(f_path)
            # 删除Unnamed列
        df_0 = df_0.loc[:, ~df_0.columns.str.match('Unnamed')]
        columns = df_0.columns
    else:
        assert model_name, 'f_path和model_name不能同时为空!'
        f_path = model_name

    assert columns is not None and f_path, 'columns, f_path都不能为空!'
    base_name = os.path.basename(f_path)
    file_name, file_format = os.path.splitext(base_name)

    file_name = rename_file_name if rename_file_name else file_name

    name_dc_ls = []
    _tmp_name_ls = []
    for c in columns:

        # 不对`id`字段进行处理
        if c.lower() in ['id', 'pk']:
            continue

        name = auto_generate_model_field_name(c)
        if name in _tmp_name_ls:
            # 有时候重复, 例如`事件`和`时间`
            old_index = _tmp_name_ls.index(name)
            warn(f'自动去重功能启动: name[{name}]重复! --- old: {name_dc_ls[old_index]}, new: {name}')
            name += f'_{_tmp_name_ls.count(name)}'
        else:
            _tmp_name_ls.append(name)

        dc = {
            'name': name,
            'verbose_name': c,
        }
        name_dc_ls.append(dc)

    # --- 获取各个字段的代码`field_codes`
    res_ls = []
    for dc in name_dc_ls:
        if add_db_column:
            _res = f'{dc.get("name")} = models.TextField(verbose_name="{dc.get("verbose_name")}", db_column="{dc.get("verbose_name")}", blank=True, null=True)'
        else:
            _res = f'{dc.get("name")} = models.TextField(verbose_name="{dc.get("verbose_name")}", blank=True, null=True)'
        res_ls.append(_res)

    # region # --- 获取model的Meta信息
    if model_name is None:
        model_name = auto_generate_model_field_name(file_name)
        # reg = re.compile(r'(_[a-z])|(^[a-z])')
        reg = re.compile(r'(^|_)[a-z]')
        find_iter = reg.finditer(model_name)
        group_ls = []
        for group in find_iter:
            group_ls.append(group.span())
        group_ls.reverse()

        for g in group_ls:
            _old_symbol = model_name[g[0]: g[1]]
            _new_symbol = _old_symbol[-1].upper()
            model_name = replace_string(model_name, _new_symbol, g[0], g[1])

        model_name = re.sub(r'\)$', '', model_name)
        model_name = re.sub(r'\(|\)|-', '_', model_name)
        model_name = re.sub('_+', '_', model_name)      # 不能有两个以上的连续空格
    # endregion

    model_verbose_name = file_name

    field_codes = '\n    '.join(res_ls)

    model_code = f"""
# 数据源文件路径: {f_path}
from django.db import models


class {model_name}(models.Model):
    class Meta:
        ordering = ['-pk']
        verbose_name_plural = verbose_name = '{model_verbose_name}'

    {field_codes}
"""
    model_info = {
        'model_name': model_name,
        'model_verbose_name': model_verbose_name,
        'model_code': model_code,
        'f_path': f_path,
        'name_dc_ls': name_dc_ls,
    }
    return model_info
# endregion


def is_run_in_exe():
    """
    判断是否已经打包为exe
    """
    ret = 0
    try:
        if hasattr(sys, "_MEIPASS") and sys._MEIPASS is not None:
            ret = 1
    except AttributeError:
        print('~~~ AttributeError ~~~')
    return ret


def my_exe_assert_function(sentence, msg, sleep_time=3):
    if not sentence:
        if is_run_in_exe():
            print(msg)
            sleep(sleep_time)
            exit()
        else:
            raise AssertionError(msg)
    return 1


def main():
    add_db_column = model_name = None

    if len(sys.argv) == 1:
        f_path = input("--- 将数据文件拖入本窗口中或拖拽至exe图标上继续, 输入回车键则退出进程:\n")
        if not f_path:
            return 0

        # --- 解决文件名含括号时的bug
        if f_path.startswith('\"') or f_path.startswith('\''):
            f_path = f_path[1:]
        if f_path.endswith('\"') or f_path.endswith('\''):
            f_path = f_path[:-1]
    elif len(sys.argv) == 2 and '-h' not in sys.argv and '--help' not in sys.argv:
        f_path = sys.argv[1]
    else:
        args = parse_args()
        f_path = args.f_path
        add_db_column = args.add_db_column
        model_name = args.model_name

    if not f_path:
        if not is_run_in_exe():
            my_exe_assert_function(False, '命令行参数错误: 数据文件路径不能为空!')

    model_info = get_model_info(f_path, model_name=model_name, add_db_column=add_db_column)
    print(model_info.get('model_code'))

    if is_run_in_exe():
        input("按回车键退出...")
        return 1


if __name__ == '__main__':
    main()

