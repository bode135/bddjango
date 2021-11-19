#!/usr/bin/env bash
: 强制pull, 将本地重置为server端版本, 然后运行.

source venv/bin/activate
: venv/Scripts/activate.bat

cd thinkTank_dj2006

git fetch --all
git reset --hard origin/bode
git pull origin bode

pip install -r r.txt

python manage.py runserver 0.0.0.0:8003