from warnings import warn
from .pure import *


def version():
    v = "2.8.1"
    return v


try:
    from .django import *
except Exception as e:
    warn('导入django失败? --- ' + str(e))

try:
    from .myFIelds import AliasField  # 这个只能在这里引用, 不然`adminclass`报错
except Exception as e:
    warn('导入`AliasField`失败? --- ' + str(e))
