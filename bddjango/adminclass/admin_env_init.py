import os
from django.conf import settings
from ..pure import TEMPDIR


DATA_UPLOAD_MAX_NUMBER_FIELDS = settings.DATA_UPLOAD_MAX_NUMBER_FIELDS


if not hasattr(settings, 'BD_USE_AJAX_ADMIN'):
    BD_USE_AJAX_ADMIN = True
else:
    BD_USE_AJAX_ADMIN = getattr(settings, 'BD_USE_AJAX_ADMIN')  # 是否使用AjaxAdmin


# --- 检测是否安装了simpleui, 以使用不同界面配置
app_ls: list = settings.INSTALLED_APPS

BD_USE_SIMPLEUI = True if 'simpleui' in app_ls or 'simpleuipro'in app_ls else False
CHANGE_LIST_HTML_PATH = os.path.join('entities', 'simpleui_change_list.html') if BD_USE_SIMPLEUI else os.path.join('entities', 'base_change_list.html')


# --- 默认检测是否simpleui + guadian, 配置object权限按钮的样式. ps: 优先使用settings中的设置.
use_guardian_settings_name = 'BD_USE_GUARDIAN'
CHANGE_FORM_TEMPLATE = 'admin/guardian/model/change_form.html'      # guardian的默认样式
if not hasattr(settings, use_guardian_settings_name):
    BD_USE_GUARDIAN = False
    if 'guardian' in app_ls:
        BD_USE_GUARDIAN = True
        if BD_USE_SIMPLEUI:
            CHANGE_FORM_TEMPLATE = 'admin/guardian/model/simpleui_guardian_change_form.html'
else:
    BD_USE_GUARDIAN = getattr(settings, use_guardian_settings_name)


# --- 加入django的templates路径
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
settings.TEMPLATES[0]['DIRS'].append(TEMPLATES_DIR)

CHANGE_LIST_HTML_PATH = os.path.join(TEMPLATES_DIR, CHANGE_LIST_HTML_PATH)

# --- 如果使用的是simpleui, 则需要修复一些bug
# https://github.com/newpanjing/simpleui/issues/405
if BD_USE_SIMPLEUI and not os.path.exists(os.path.join('templates', 'admin', 'actions.html')):
    from django.contrib.admin.templatetags.admin_list import admin_actions, InclusionAdminNode, register
    template_name = 'simpleui_admin_actions.html'

    @register.tag(name='simpleui_admin_actions')
    def simpleui_admin_actions(parser, token):
        return InclusionAdminNode(parser, token, func=admin_actions, template_name=template_name)

    CHANGE_LIST_HTML_PATH = os.path.join(TEMPLATES_DIR, 'entities', 'simpleui_change_list_actions.html')


def create_dir_if_not_exist(dirpath: str):
    if not os.path.exists(dirpath):
        os.mkdir(dirpath)
        return False
    return True


create_dir_if_not_exist(TEMPDIR)


if __name__ == '__main__':
    pass
