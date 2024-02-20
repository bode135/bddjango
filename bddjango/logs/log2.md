# bddjango版本更新


## 相关链接

- [wiki文档地址_内网](https://www.bodexiong.vip/mkdocs/)
- [wiki文档地址_外网](https://wiki-bddjango.readthedocs.io/zh/)
- [pypi项目地址](https://pypi.org/project/bddjango/)
- [查看当前最新版本号](https://pypi.org/search/?q=bddjango)


## 更新信息

### 2.8.1
- 更改项目信息
- 整合Readme.md文件

### 2.8.2
- test

# 2.8.3
- 导入导出数据AdminMixin开放给前端

# 2.8.4
- 导入导出优化, `.save`改为`.create`

# 2.8.5
- 导入导出修复: 解决了数据库中str字段导入时被pandas解析为float的bug

# 2.8.6
- 修复导出文件时, 空文件报错的bug

# 2.8.7
- 修复导出文件时, 有FileField字段导致报错的bug
- 可能还存在导出时有`None`没替换为空白的情况.

# 2.8.8
- 修复导入文件时, 有`DateField`时间格式字段解析失败的bug

# 2.8.9
- 日期时间字段导入优化

# 2.9.1
- `get_key_from_request_data_or_self_obj`支持字典
- `convert_query_parameter_to_bool`的false增加['f', 'F', '__None__', ['__None__']]

# 2.9.2
- 解决get_key_from_request_data_or_self_obj有None时报错(get_list方法在dict时返回None)

# 2.9.3
- admin_list页面默认不再自动加一个link字段

# 2.9.4
- pg和sqlit3的兼容(如distinct问题, 写入数据时sqlite3不支持多线程的问题)
- 增加功能`autoCode.py`

# 2.9.5
- `autoCode.py`只允许选中一条数据

# 2.9.6
- autoCode增加default_use_complete_model_view参数

# 2.9.7
- `autoCode.py`:
    - 增加`auto_model`功能
    - 注册`content_type`流程简化为`register_content_type_admin`
- 增加`tools`文件夹
- `__init__.py`增加`get_root_path`方法
- `create_user_if_not_exist`方法优化, 将自动检测数据库是否正在`migrate`中

# 2.9.8
- 修复`auto_code`耗时估计错误的小bug


# 2.9.9
- 修复`auto_code`导入admin时没有`adminclass`的错误
- 修复`auto_code`的`app_label`错误
- 修复导入数据时`curr_id`错误导致多线程报错的bug, 并增加参数`workers`取代`bulk_size`
- admin默认显示总共多少条数据
- 增加AddTimes类
- 给ListStatisticMixin增加order_config_dc_ls字段, 方便自定义特殊字段的排序















