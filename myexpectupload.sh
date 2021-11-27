#!/usr/bin/expect
# 自动上传pypi
# command: `expect xxx.sh`

# 加载密码
set username [lindex $argv 0];
set password [lindex $argv 1];

# 设置超时时间
set timeout 5


# 自动上传pypi
spawn twine upload dist/*
expect "Enter your username:" {
    send $username\n"
}
expect "password" {
    send "$password\n"
}


#保持在远端
interact
exit
