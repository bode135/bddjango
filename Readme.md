# 初始化


- 兼容Django-4.0和Django-5.0


## 3.6以上兼容



### 1. 报错`No module named packaging`

```
pip3 install --upgrade pip
pip3 install packaging
```





## win

```
# 获取脚本
python tools\getshell.py

# 迁移
shells\wmigrate.bat
shells\wmigrate.bat file_upload

# shells\wmigrate.bat index

```



## linux or mac

```
# 获取脚本
python tools/getshell.py

# 迁移
bash shells/migrate.bat
bash shells/migrate.bat file_upload

# bash shells/migrate.bat index

```



## 运行参数

```
python manage.py runserver
```



## 环境变量

```
PYTHONUNBUFFERED=1;LANG=C.UTF-8;PYTHONIOENCODING=utf-8
```



## 后台界面

- 密码在`file_upload/admin.py`中通过`create_user_if_not_exist`设置
- [后台地址](http://127.0.0.1:8000/api/admin/)


