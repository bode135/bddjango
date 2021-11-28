#!/usr/bin/env bash
: 杀死指定端口, linux和mac版本

# 加载用户名和密码
source authinfo.sh

echo "-------- begging auto submit ---------"
echo "--- your username: $username"
echo "--- passwd: $passwd"
sleep 1.5

# git更新, 删除旧文件, 编译新文件, expect自动上传pypi
echo -e "\n\n--------------- begging git pull -------------------------\n"
git pull
echo -e "--------------- git pull successful. -----------------\n\n" && sleep 2

rm -rf build dist
python setup.py sdist bdist_wheel
echo -e "\n\n-------- build: build successful.\n\n" && sleep 2

expect myexpectupload.sh $username $passwd
echo -e "\n-------- expect: end auto submit." && sleep 2
