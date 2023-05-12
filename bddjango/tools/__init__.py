import os
import shutil
from .sort_dc_ls1_by_ls2 import sort_dc_ls1_by_ls2


def copy_tools_to_cwd(basename=None):
    dir_path = os.path.dirname(__file__)
    basename = basename if basename else os.path.basename(dir_path)
    if os.path.exists(basename):
        print(f'无法拷贝{dir_path}至当前路径, {basename}已存在!')
    else:
        shutil.copytree(dir_path, basename)




