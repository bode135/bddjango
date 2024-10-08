"""
将nginx的配置文件替换为当前文件下的`default`, 并重启nginx
"""

import os
import platform
import shutil


assert platform.system() == 'Linux', "必须是`Linux`版本!"


if os.system('which apt') == 0:
    is_ubuntu = True
elif os.system('which yum') == 0:
    is_ubuntu = False
else:
    raise TypeError("安装包管理器不是apt也不是yum?")

package_manager = "apt-get" if is_ubuntu else "yum"
os.system(f"{package_manager} install -y nginx")

if is_ubuntu:
    dst = "/etc/nginx/sites-available/default"
    _dst = "/etc/nginx/tmp/_default"

    src = os.path.join(os.path.dirname(__file__), "default")
else:
    dst = "/etc/nginx/conf.d/default.conf"
    _dst = "/etc/nginx/tmp/_default.conf"
    src = os.path.join(os.path.dirname(__file__), "default")

# 备份一下原配置文件
try:
    if os.path.exists(dst) and not os.path.exists(_dst):
        tmp_dir = "/etc/nginx/tmp/"
        os.makedirs(tmp_dir, exist_ok=True)
        shutil.copy2(_dst, dst)
except Exception as e:
    print(f'*** backup fail, error: {e}')

print(f'--- src: [{src}] -> dst: [{dst}]')
shutil.copy2(src, dst)
os.system("service nginx restart")

print("nginx配置已更新, 记得收集静态文件`python manage.py collectstatic --noinput`")

