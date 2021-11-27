#!/usr/bin/env bash
# 强制pull, 将本地重置为server端版本.

branch=master

git fetch --all
git reset --hard origin/$branch
git pull origin $branch
