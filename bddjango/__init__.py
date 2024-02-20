from warnings import warn
from .pure import *


def version():
    v = "3.0.8"
    return v


def get_root_path():
    path = os.path.dirname(__file__)
    return path


try:
    from .django import *
except Exception as e:
    warn('导入django失败? --- ' + str(e))

