from django.contrib.auth import get_user_model
import sys


def judge_db_is_migrating():
    if 'makemigrations' in sys.argv or 'migrate' in sys.argv:
        return True
    else:
        return False


def create_user_if_not_exist(username, passwd, superuser=False, extra_fields=None):
    """
    创建一个用户
    """
    if judge_db_is_migrating():
        return
    User = get_user_model()
    user = User.objects.filter(username=username)
    if not user.exists():
        print(f'--- 初始创建用户: {username}')

        fields_dc = {}
        fields_dc.update({'username': username, "password": passwd})

        if isinstance(extra_fields, dict):
            fields_dc.update(extra_fields)

        if superuser:
            User.objects.create_superuser(**fields_dc)
        else:
            User.objects.create_user(**fields_dc)
        return True
    else:
        return False
