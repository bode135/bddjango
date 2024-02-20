"""
解压文件
"""


def unzip_to(src, dst, overwrite=True):
    """
    解压src到dst路径

    :param src: 来源
    :param dst: 目标
    :param overwrite: `True`则覆盖, 否则增量上传
    """
    from bdtime import Time
    import shutil
    import zipfile
    import re
    import os
    from .remove_temp_file import remove_temp_file
    from bddjango import copy_to, remove_path

    tt = Time()
    TEMPDIR = 'tempdir'

    assert dst not in ['/'], f"别乱搞哦! 检测到[replace_path: {dst}]有安全性问题! 不允许替换根路径!"

    assert zipfile.is_zipfile(src), '仅支持zip文件!'

    assert dst.endswith('/'), "目标路径若是文件夹, 填写的时候必须以`/`符号结尾!"
    dir_name = os.path.basename(os.path.dirname(dst))
    os.makedirs(dst, exist_ok=True)

    zf = zipfile.ZipFile(src, 'r')

    zip_dir_root_name = "temp_zip_dir"
    temp_zip_root_path = os.path.join(TEMPDIR, zip_dir_root_name)
    os.makedirs(temp_zip_root_path, exist_ok=True)

    temp_file = f"zip_extract__{tt.time().__str__().replace('.', '')}"
    temp_path = os.path.join(temp_zip_root_path, temp_file)

    for file in zf.namelist():
        zf.extract(file, temp_path)

    reg = re.compile(r'[\u4e00-\u9fa5]')
    assert not reg.search(dir_name), '最外层文件夹名称不能含中文!'

    unzip_dirpath = os.path.join(temp_path, dir_name)
    f_ls = os.listdir(temp_path)
    mac_os_dir = '__MACOSX'
    if mac_os_dir in f_ls:
        f_ls.remove(mac_os_dir)

    if not os.path.exists(unzip_dirpath) and len(f_ls) == 1:
        p0 = os.path.join(temp_path, f_ls[0])
        if os.path.isdir(p0):
            os.rename(p0, unzip_dirpath)

    if not os.path.exists(unzip_dirpath):
        from warnings import warn
        warn(f'*** 解压后未找到目标文件夹`{dir_name}`! 最好确保压缩包双击打开后最外层只有一个`{dir_name}`文件夹! 将尝试自动解决...')
        os.mkdir(unzip_dirpath)
        for f_i in f_ls:
            copy_to(os.path.join(temp_path, f_i), os.path.join(unzip_dirpath, f_i))

    assert os.path.exists(unzip_dirpath), f'解压后未找到目标文件夹`{dir_name}`! 请确保压缩包双击打开后最外层只有一个`{dir_name}`文件夹.'

    # region # --- 处理中文乱码问题
    def rename_error_codes(src_path, dst_path=None):
        assert os.path.isdir(src_path), 'src_path必须为文件夹类型!'
        if dst_path is None:
            dst_path = src_path

        _file_ls = os.listdir(src_path)
        for i in range(len(_file_ls)):
            try:
                _file_i = _file_ls[i]
                try:
                    file_i = _file_i.encode('cp437').decode('gbk')
                except:
                    try:
                        file_i = _file_i.encode('cp437').decode('utf-8')
                    except:
                        raise TypeError('文件名编码解析错误! 请保证zip压缩包内均为gbk或utf-8编码命名的文件!')
                rename_src = os.path.join(src_path, _file_i)
                rename_dst = os.path.join(dst_path, file_i)
                if os.path.isfile(rename_src):
                    copy_to(rename_src, rename_dst, overwrite=False)
                else:
                    os.makedirs(rename_dst, exist_ok=True)
                    rename_error_codes(rename_src, rename_dst)
                if rename_src != rename_dst:  remove_path(rename_src)
            except Exception as e:
                print(e)
    rename_error_codes(unzip_dirpath)
    # endregion

    if overwrite:
        # --- 将 temp_path 拷贝至 dst
        if os.path.exists(dst):
            shutil.rmtree(dst)

        shutil.copytree(unzip_dirpath, dst)
    else:
        src = unzip_dirpath
        copy_to(src, dst, overwrite=False)

    remove_temp_file(temp_zip_root_path)


