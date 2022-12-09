from warnings import warn
from .pure import *


def version():
    v = "2.9.7"
    return v


try:
    from .django import *
except Exception as e:
    warn('导入django失败? --- ' + str(e))


def get_root_path():
    path = os.path.dirname(__file__)
    return path
