"""
将nginx的配置文件替换为当前文件下的`default`, 并重启nginx
"""

import os
import platform
import shutil

assert "Ubuntu" in platform.platform(), "必须是Ubuntu版本, 不支持Centos等其它版本!"
os.system("apt-get install -y nginx")

dst = "/etc/nginx/sites-available/default"
src = os.path.join(os.path.dirname(__file__), "default")

shutil.copy2(src, dst)
os.system("service nginx restart")

print("nginx配置已更新.")
