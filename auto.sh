#!/usr/bin/env bash
: 杀死指定端口, linux和mac版本

# 加载用户名和密码
source authinfo.sh


echo $username
echo $passwd

# git更新, 删除旧文件, 编译新文件, expect自动上传pypi
git pull
rm -rf build dist
python setup.py sdist bdist_wheel
prinrf "\n\n--- $username expect: end auto build.\n\n" && sleep 1

expect myexpectupload.sh $username $passwd
prinrf "\n\n--- $username expect: end auto submit.\n\n" && sleep 1
