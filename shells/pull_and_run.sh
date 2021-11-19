#!/usr/bin/env bash
: 拉取最新版并运行.

source venv/bin/activate

cd legislationYunnan_dj2110

git pull origin bode

pip install -r requirements.txt

python manage.py runserver 0.0.0.0:8003