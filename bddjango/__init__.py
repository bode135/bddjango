from warnings import warn
from .pure import *
from .tools.version_monkey_patch.package_version_utils import get_package_version, is_version_greater_than

version_str = get_package_version("django")
assert version_str is not None, "Get version failed, package[django] is not installed!"
if is_version_greater_than(version_str, "4.0"):
    import django
    from django.utils.encoding import force_str
    django.utils.encoding.force_text = force_str
    from urllib.parse import quote
    django.utils.http.urlquote = quote


def version():
    v = "3.0.9"
    return v


def get_root_path():
    path = os.path.dirname(__file__)
    return path


try:
    from .django import *
except Exception as e:
    warn('导入django失败? --- ' + str(e))

