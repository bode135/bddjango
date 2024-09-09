#!/usr/bin/env bash
: 迁移脚本


input=$1
python manage.py makemigrations $input
python manage.py migrate $input

