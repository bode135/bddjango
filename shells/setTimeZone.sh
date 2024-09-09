#!/usr/bin/env bash
: 设置时区

TZ=Asia/Shanghai
sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list
apt-get update
ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
apt-get install tzdata
apt-get clean
apt-get autoclean
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
