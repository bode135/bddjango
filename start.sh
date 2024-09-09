#!/usr/bin/env bash
# 用screen来启动指定shell命令

LANG=C.UTF-8
PYTHONIOENCODING=utf-8

# kill all died screen sessions
screen -wipe
#pkill screen


if [ $# == 0 ];then
    echo "没有带参数";
    screen_name=start;
    screen_shell='bash .start.sh\n';
else
    echo "--- 带了$#个参数.. ---";
    if [ $# == 1 ]; then echo "*** Error: 参数必须大于等于两个, 分别为screen_name和screen_shell! ---"; exit; fi
    screen_name=$1
    screen_shell=$2
fi

echo "screen_name --- $screen_name"
echo "screen_shell --- $screen_shell"


screen -ls | grep $screen_name | awk '{print $1}' | xargs -I {} screen -X -S {} quit
#screen -X -S $screen_name quit


xx=$(screen -ls | grep $screen_name)
if [ ! ${xx} ];
then
    echo "will create a new screen! --- screen_name: ${screen_name}";
    screen -dmS $screen_name;
else
		echo "already created screen!";
fi

#screen -S $screen_name -X stuff "bash .start.sh\n"
#screen -S $screen_name -X stuff "bash updater_start.sh\n"

# screen -S $screen_name -X stuff 'LANG=C.UTF-8 && PYTHONIOENCODING=utf-8 && source /root/.bashrc && PYTHONIOENCODING=utf-8 python auto_updater.py\n'
screen -S $screen_name -X stuff "$screen_shell"
#screen -S $screen_name -X stuff 'bash .start.sh\n'





