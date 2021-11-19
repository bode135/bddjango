#!/usr/bin/env bash
: Django数据库操作

commit_name="$1"
python manage.py makemigrations commit_name
python manage.py migrate commit_name
