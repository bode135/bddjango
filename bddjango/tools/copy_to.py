import os
import shutil
from .remove_temp_file import remove_path


def copy_to(src, dst, overwrite=True, is_overwrite_same_name_files=True, dbg=False):
    """
    将src拷贝至dst路径, 同时支持file和directory类型

    :param src: 来源路径
    :param dst: 目标路径
    :param overwrite: `True`则直接覆盖目标路径, `False`则为`增量替换`
    :param dbg: 输出debug信息
    :param is_overwrite_same_name_files: `overwrite`为`增量替换`时生效, `True`则`直接替换同名文件`, `False`忽略同名文件
    """
    if dst == src:
        if dbg:
            print(f'--- copy_to: src和dst相等? value: {[src]}')
        return

    if overwrite:
        remove_path(dst)

        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    else:
        if os.path.isdir(src):
            if os.path.exists(dst):
                assert os.path.isdir(dst), '类型不匹配: 源路径和目标路径的类型必须均为文件夹!'
            else:
                shutil.copytree(src, dst)

            s_files = os.listdir(src)
            d_files = os.listdir(dst)
            if dbg:
                print('s_files --- ', s_files)
                print('d_files --- ', d_files)

            for s_f in s_files:
                _src = os.path.join(src, s_f)
                _dst = os.path.join(dst, s_f)

                if s_f in d_files:
                    if is_overwrite_same_name_files:
                        if dbg:
                            print(f'--- dir: 将删除目标路径[{_dst}]')
                        remove_path(_dst)
                    else:
                        if dbg:
                            print(f'--- dir:目标路径[{s_f}]已存在, 且忽略了本次替换')

                if os.path.isfile(_src):
                    shutil.copy2(_src, _dst)
                else:
                    shutil.copytree(_src, _dst)

        else:
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
            else:
                if is_overwrite_same_name_files:
                    if dbg:
                        print(f'--- file: 将删除目标路径[{dst}], 用[{src}]替换!')
                    remove_path(dst)
                    shutil.copy2(src, dst)
                else:
                    if dbg:
                        print(f'--- dir: 目标路径[{dst}]已存在, 且忽略了本次替换')

