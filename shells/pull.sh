#!/usr/bin/env bash

branch=master
git pull origin $branch

echo "-----------------\n"
echo "pull时间: $(date +%Y/%m/%d) $(date +%H:%M:%S)"


