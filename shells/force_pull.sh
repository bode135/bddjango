#!/usr/bin/env bash
# 强制pull, 将本地重置为server端版本. 可使用branch指定分支

if [ $# == 0 ];then
#    branch=bode
#    echo "没有带参数, 默认为[$branch]分支";
    echo '请指定branch参数!'
    exit
else
    echo "带了$#个参数, 切换为[$1]分支";
    branch="$1";
fi

git fetch --all
git reset --hard origin/$branch
git pull origin $branch



