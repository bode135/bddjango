#!/usr/bin/env bash
# 强制pull, 将本地重置为server端版本.

git fetch --all
git reset --hard origin/master
git pull origin master
