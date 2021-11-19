#!/usr/bin/env bash
: 杀死指定端口, linux和mac版本

if [[ $# == 0 ]];then
    commit_name="8000";
    echo "----没有带参数, 默认杀死[$commit_name]端口-----";
else
    echo "带了$#个参数";
    commit_name="$1";
fi

# 调整当前工作路径(生命周期为本脚本)
root_filepath="$(pwd)/$0"
root_dirpath=$(dirname -- $root_filepath)
cd $root_dirpath

# cd $(dirname -- $(pwd)/$0)

python pykill_port.py $commit_name