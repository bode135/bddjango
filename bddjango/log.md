# bddjango版本更新


## 相关链接

- [wiki文档地址_内网](https://www.bodexiong.vip/mkdocs/)
- [wiki文档地址_外网](https://wiki-bddjango.readthedocs.io/zh/)
- [pypi项目地址](https://pypi.org/project/bddjango/)
- [查看当前最新版本号](https://pypi.org/search/?q=bddjango)


## 更新信息

# 3.0.0
- 增加`BulkUpdateMixin`
- 统计方法增加`loc_ls`字段
- 精简项目结构
- autocode兼容gbk格式csv等
- 生成代码时使用render来返回html格式

# 3.0.1
- `copy_to`增量上传的同名文件策略改为默认替换
- `auto_wiki`, `auto_code`, `auto_model`界面优化
- 增加`BaseOrmSearchModel`, 进行相关性检索
- 增加前端控制`search_fields_conf`参数
- order_by_order_type_ls对OrderByObject进行兼容
- 在tools中增加`CsrfExemptSessionAuthentication`方法
- migrate出错导致ContentType对应的base_model为None时, 自动删除对应的obj.
- 修复auto_code的'<pk>'在html的<pre>标签中被转义的bug
- tools中增加一个`fake_model.py`
- 修复导出数据外键值为None时报错的bug
- 文件下载类`DownloadFileMixin`

# 3.0.2
- 完善导入进度条显示条件, 加入参数`single_import_threshold`
- `set_query_dc_value`增加支持`dict`类型

# 3.0.3
- 解决`statistic_dc`统计时`loc_ls`不在`df.index`而导致报错的bug
- 待解决: `django.models.py`和`jieba`形成了依赖关系
- set_query_dc_value出bug
- `BaseListView`性能优化
- 使用md5缓存, 优化`get_count`方法
- 解决`jieba`的依赖关系
- `ListStatisticMixin`的统计结果加上缓存时间`cache_expired_time__statistic_dc`

# 3.0.4
- 导出的excel格式改为`xlsx`
- 对`base_orm_search`进行调整, 以适应`union_search`
- 时间格式兼容性优化, 兼容"2022-03-01"格式
- 关键词统计Mixin: `tools.statistic_keywords_mixin.StatisticKeywordsMixin`
- bddjango的bulk_list报错问题
- 加入`BD_DEFAULT_EXPORT_FORMAT`参数, 可设置export的导出文件格式
- BaseListView的run_list_filter, 注释`self.queryset = self.get_queryset()`
- 移除对`xlrd==1.2.0`的依赖

# 3.0.5
- 正式修改依赖项

# 3.0.6
- pandas导入数据时, `how`和`thresh`不能共存的问题

# 3.0.7
- get_key_from_request_data_or_self_obj优化为False的条件

# 3.0.8
- 生成代码与xlrd解耦


