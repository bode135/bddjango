#!/usr/bin/env bash
# 目标文件夹转为unix编码

if [ $# == 0 ];then
    echo "没有带参数, 默认转换当前文件夹下的文件为linux格式";
    input=".";
else
    input="$1";
    echo "带了$#个参数, input: ${input}";
fi

find ${input} -type f -exec dos2unix {} {} \;
