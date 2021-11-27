#!/usr/bin/expect
# 自动上传pypi
# command: `expect xxx.sh`

#设置超时时间
set timeout 10

#私人密码
set username bode135
set password 1351738a

# 自动上传
spawn python setup.py sdist bdist_wheel

spawn echo "~~~~~~~~"
spawn echo "~~~~~~~~"
spawn echo "~~~~~~~~"
spawn sleep 1.5

spawn twine upload dist/*

#根据输出传递数据
expect "Enter your username:" {
    send $username\n"
}
expect "password" {
    send "$password\n"
}


#保持在远端
interact
exit

