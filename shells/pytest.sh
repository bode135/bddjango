#!/usr/bin/env bash
: pytest 单元测试脚本 测试本地环境
: 运行方法 -> sh pytest.sh

if [[ $# == 0 ]];then
    echo "没有带参数, 测试指定文件目录下的测试文件 -> tests/*";
    commit_name="tests";
    log_fpath=report/log.html
else
    echo "带了$#个参数";
    commit_name="$1";
    log_fpath=report/"$commit_name".html
fi

: 默认测试本地的接口
cp tests/urls/local_request_url tests/request_url
pytest "$commit_name" --html="$log_fpath"
open "$log_fpath"

echo "\n测试目标: $commit_name, log保存路径: $log_fpath\n"
