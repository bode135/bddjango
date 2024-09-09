#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
from tools import package_version_utils

version_str = package_version_utils.get_package_version("django")
if package_version_utils.is_version_greater_than(version_str, "3.9.9"):
    """
    兼容一下4.0版本后migrate时出错问题
    """
    from django.utils.encoding import force_str
    import django
    django.utils.encoding.force_text = force_str

if package_version_utils.is_version_greater_than(version_str, "5.0.0"):
    import datetime
    from django.utils import timezone
    timezone.utc = datetime.timezone.utc
    v_drf = package_version_utils.get_package_version("djangorestframework")
    target_v = '3.15.2'
    assert package_version_utils.is_version_greater_than(v_drf, target_v, can_equal=True),\
        f"Version of `djangorestframework` must greater than `{target_v}`! run `pip install -U djangorestframework>={target_v}`"


import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ControlHub.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
