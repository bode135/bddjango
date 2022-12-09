import os
import shutil


def sort_dc_ls1_by_ls2(dc_ls1, key, ls2=None, reverse=False):
    """
    将dc_ls1按key字段排序, 排序顺序可以指定为ls2.
    """
    if ls2 is not None:
        res = [i for j in ls2 for i in dc_ls1 if i.get(key) == j]  # show_ls(info_dc_ls)
        if reverse:
            res.reverse()
    else:
        res = sorted(dc_ls1, key=lambda k: k[key], reverse=reverse)
    return res


def copy_tools_to_cwd(basename=None):
    dir_path = os.path.dirname(__file__)
    basename = basename if basename else os.path.basename(dir_path)
    if os.path.exists(basename):
        print(f'无法拷贝{dir_path}至当前路径, {basename}已存在!')
    else:
        shutil.copytree(dir_path, basename)




