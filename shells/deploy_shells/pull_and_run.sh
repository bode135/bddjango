#!/usr/bin/env bash
: source venv/bin/activate
source activate market

: venv/Scripts/activate.bat

cd siShiZhuanTiKu_django2118

git pull origin bode

pip install -r r.txt

python manage.py runserver 0.0.0.0:2118