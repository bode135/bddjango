"""
获取用户ip
"""


def get_user_ip(request):
    meta = request.META
    if 'HTTP_X_FORWARDED_FOR' in meta:
        ip = meta['HTTP_X_FORWARDED_FOR']
    elif 'REMOTE_ADDR' in meta:
        ip = meta['REMOTE_ADDR']
    else:
        raise ValueError('ip地址获取错误!')

    return ip
