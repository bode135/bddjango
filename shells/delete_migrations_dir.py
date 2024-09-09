"""
# 清理django-migrations的脚本

- 删除二级路径中的 migrations文件夹(destination_dir_name)
- 多系统兼容

"""


import os
import shutil


# destination_dir_name = "test111"
destination_dir_name = "migrations"


def main():
    dir_ls = os.listdir(".")

    migrations_path_ls = []
    for dir_i in dir_ls:
        if not os.path.isdir(dir_i):
            continue

        _dir_ls = os.listdir(dir_i)
        for _dir_i in _dir_ls:
            _dir_path = os.path.join(dir_i, _dir_i)
            if not os.path.isdir(_dir_path):
                continue

            if _dir_i == destination_dir_name:
                migrations_path_ls.append(_dir_path)

    for migrations_path_i in migrations_path_ls:
        print(migrations_path_i)
        shutil.rmtree(migrations_path_i)


if __name__ == '__main__':
    main()
