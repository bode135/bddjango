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
echo "\n\n--- expect: end auto build.\n" && sleep 1

expect myexpectupload.sh $username $passwd
echo "\n\n--- expect: end auto submit.\n" && sleep 1
