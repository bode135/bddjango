from warnings import warn
from .pure import *
try:
    from .django import *
except Exception as e:
    warn('导入django失败? --- ' + str(e))