#!/usr/bin/env bash
: fake迁移脚本

#  app_name
input=$1;
# does delete migrations dir
remove_migrations=$2;


if [ $# == 0 ];then
    echo "没有带参数";
else
    if [ remove_migrations = "1" ];then
        echo -e "\n*** program will delete the [$input/migrations]!\n";
        sleep 2;
        rm -rf $input/migrations/;
    fi
    python manage.py makemigrations --empty $input;
fi

python manage.py makemigrations $input;
python manage.py migrate --fake $input;


