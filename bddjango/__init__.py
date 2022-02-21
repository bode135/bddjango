from warnings import warn
from .pure import *
try:
    from .django import *
    from .myFIelds import AliasField        # 这个只能在这里引用, 不然`adminclass`报错
except Exception as e:
    warn('导入django失败? --- ' + str(e))