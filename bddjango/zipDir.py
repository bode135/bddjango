import os
import zipfile
import re


def zipDir(dirpath, outFullName, remove_root_dir_path=None):
    """
    压缩指定文件夹
    :param dirpath: 目标文件夹路径
    :param outFullName: 压缩文件保存路径+xxxx.zip
    :param remove_root_dir_path: 是否去掉目标根路径. 若为str, 则删除该根路径文件名, 若为1, 则删除所有根路径.
    :return: 无
    """

    if remove_root_dir_path is None:
        # 保留目标根路径
        with zipfile.ZipFile(outFullName, 'w') as target:
            for i in os.walk(dirpath):
                for n in i[2]:
                    target.write(''.join((i[0], '\\', n)))

    elif isinstance(remove_root_dir_path, str):
        with zipfile.ZipFile(outFullName, "w", zipfile.ZIP_DEFLATED) as zip:
            for path, dirnames, filenames in os.walk(dirpath):
                # path = path.replace('/', '\\')
                path = path.replace('/', os.sep)
                remove_root_dir_path = remove_root_dir_path.replace('/', os.sep)
                if remove_root_dir_path.endswith('\\') or remove_root_dir_path.endswith('/'):
                    remove_root_dir_path = remove_root_dir_path[:-1]

                # 去掉目标根路径，只对目标文件夹下边的文件及文件夹进行压缩
                # fpath = path.replace(dirpath, '')
                pattern = fr"""^{remove_root_dir_path.encode('unicode_escape').decode('ascii')}"""
                fpath = re.sub(pattern, '', path)
                print(path, '---', fpath, filenames)

                for filename in filenames:
                    # if fpath.startswith(remove_root_dir_path):
                    #     # 大坑, 注意re使用fr-string需要重新编码!
                    #     pattern = fr"""^{remove_root_dir_path.encode('unicode_escape').decode('ascii')}"""
                    #     # pattern = fr"""^{remove_root_dir_path}"""     # 不行
                    #     fpath = re.sub(pattern, '', fpath)
                    #     # fpath = fpath[len(remove_root_dir_path):]
                    # fpath = re.sub(r'^' + remove_root_dir_path, '', fpath)
                    print(os.path.join(path, filename), '------', os.path.join(fpath, filename))
                    zip.write(os.path.join(path, filename), os.path.join(fpath, filename))

    elif remove_root_dir_path == 1:
        with zipfile.ZipFile(outFullName, "w", zipfile.ZIP_DEFLATED) as zip:
            for path, dirnames, filenames in os.walk(dirpath):
                # 去掉目标根路径，只对目标文件夹下边的文件及文件夹进行压缩
                fpath = path.replace(dirpath, '')
                for filename in filenames:
                    zip.write(os.path.join(path, filename), os.path.join(fpath, filename))


if __name__ == "__main__":
    input_path = "tempdir/预报名表_20211221_190018"
    output_path = "./test.zip"

    zipDir(input_path, output_path, remove_root_dir_path='tempdir/')
    # zipDir(input_path, output_path, remove_root_dir_path=1)