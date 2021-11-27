#!/usr/bin/env bash
# git提交修改的脚本

if [ $# == 0 ];then
    echo "没有带参数";
    commit_name="代码完善";
else
    echo "带了$#个参数";
    commit_name="$1";
fi


# --- args
branch=master

# --- commands
git add .
git commit -m "$commit_name"
git push -u origin $branch

echo "\n提交说明为: $commit_name\n"

echo "Press enter to continue..."
read continue
echo "Your continue is $continue"
echo
