#! /usr/bin/expect
 
# 自动登录服务器, 然后再运行脚本

# 使用expect+ssh自动登录服务器, 并运行指定sh脚本
# -- root@10.120.65.140
set timeout 5
set userName root
set host 10.120.65.140
set passwd root123

spawn ssh $userName@$host
 
expect {
    "(yes/no)?" {
        send "yes\n"
        expect "password:"
        send "$passwd\n"
    }
    "*password:" {
        send "$passwd\n"
    }
}
# 加载项目的虚拟环境
expect {
    "base" {
	send "cd ~/mysource/\n"
    }
}

 
interact
exit


