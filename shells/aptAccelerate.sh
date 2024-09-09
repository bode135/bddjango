#!/usr/bin/env bash
# apt-get加速

echo "Asia/Shanghai" > /etc/timezone && dpkg-reconfigure -f noninteractive tzdata && echo "deb http://mirrors.aliyun.com/debian/ buster main non-free contrib" > /etc/apt/sources.list

apt update

