import os
import shutil
from django.conf import settings
from ..pure import version


# --- 检测是否安装了simpleui, 以使用不同界面配置
app_ls: list = settings.INSTALLED_APPS
BD_USE_SIMPLEUI = True if 'simpleui' in app_ls or 'simpleuipro'in app_ls else False
CHANGE_LIST_HTML_PATH = os.path.join('entities', 'simpleui_change_list.html') if BD_USE_SIMPLEUI else os.path.join('entities', 'base_change_list.html')
if not os.path.exists(CHANGE_LIST_HTML_PATH):
    """
    没有dir, 就用bddjango默认的templates模板
    """
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
    CHANGE_LIST_HTML_PATH = os.path.join(TEMPLATES_DIR, CHANGE_LIST_HTML_PATH)
    settings.TEMPLATES[0]['DIRS'].append(TEMPLATES_DIR)


# --- 初始化环境 --- 已经不用了 -------------------
def create_dir_if_not_exist(dirpath: str):
    if not os.path.exists(dirpath):
        os.mkdir(dirpath)
        return False
    return True


def run():
    src1 = os.path.join(os.path.dirname(__file__), 'templates', 'admin', 'csv_form.html')
    dst1 = os.path.join('templates', 'admin')

    src2 = os.path.join(os.path.dirname(__file__), 'templates', 'entities', 'mychange_list.html')
    dst2 = os.path.join('templates', 'entities', 'mychange_list.html')

    src3 = os.path.join(os.path.dirname(__file__), 'templates', 'entities', 'basechange_list.html')
    dst3 = os.path.join('templates', 'entities', 'basechange_list.html')

    if os.path.exists(dst1) and os.path.exists(dst2) and os.path.exists(dst3):
        return

    print(f'\n------ 首次引入bddjango v{version()}, 初始化templates文件夹 ------\n')

    create_dir_if_not_exist('templates')
    create_dir_if_not_exist(os.path.join('templates', 'admin'))
    create_dir_if_not_exist(os.path.join('templates', 'entities'))

    shutil.copy2(src1, dst1)
    shutil.copy2(src2, dst2)
    shutil.copy2(src3, dst3)


if __name__ == '__main__':
    run()