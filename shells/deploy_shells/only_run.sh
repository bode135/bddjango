#!/usr/bin/env bash
source venv/bin/activate

cd thinkTank_dj2006

: git pull origin bode

: pip install -r r.txt

python manage.py runserver 0.0.0.0:8003