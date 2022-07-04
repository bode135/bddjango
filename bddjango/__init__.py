from warnings import warn
from .pure import *


def version():
    """
    * 2021/6/1
    - [pypi_url](https://pypi.org/project/bddjango/)

    # 2.2
        - 方法version转移到__init__.py中
        - 修改由`get_key_from_query_dc_or_self`引起的bug
        - 高级检索类增加`search_ls_dc`和`search_conf`两个参数
        - 修改由于readme.md出错导致pypi上传失败的bug	# 2.2.2
        - 去掉部分print	# 2.2.3
        - 新增conv_to_queryset方法	# 2.2.3
        - 修复部分bug	# 2.2.4
    # 2.3 baseDjango项目
        - StateMsgResultJSONRenderer错误提示    # 2.3.0
        - autoWiki部分修改
        - _remove_temp_file修改为默认保存最近访问过的1/3缓存文件
        - BaseListView支持orm参数, 并可使用`convert_to_bool_flag`强制转换为bool变量
        - 拆分.django文件
        - 增加`.django.judge_db_is_migrating`, 来判断是否正在迁移数据库
        - 将`remove_temp_file`迁移至.pure中      # 2.3.1
        - 将adminclass中的导入导出类增加权限验证和自定义取消功能
        - 将adminclass中的导出action增加取消功能       # 2.3.2
    # 2.4 贵州图书馆项目
        - `get_base_serializer`增加`auto_generate_annotate_fields`功能
        - 修复了`run_list_filter`中的`annotate`字段检索失效的问题
        - `AutoWiki`增加mac兼容
        - BaseListView的retrieve修复queryset中annotate字段失效问题
        - 修复get_base_serializer在queryset进行values后annotate字段失效问题
        - 修复get_key_from_query_dc_or_self当query_dc中有False时返回值出错的bug
        - 修复get_key_from_query_dc_or_self当query_dc中获取bool错误问题       # 2.4.1
        - get_MySubQuery增加注释
        - order_qs_ls_by_id完善为不限制长度
        - zip功能完善       # 2.4.2
        - get_base_serializer解决'__all__'和retrieve时出现的bug        # 2.4.3
        - retrieve_filter_field现在可由前端指定
    """
    v = "2.4.3"
    return v


try:
    from .django import *
except Exception as e:
    warn('导入django失败? --- ' + str(e))

try:
    from .myFIelds import AliasField        # 这个只能在这里引用, 不然`adminclass`报错
except Exception as e:
    warn('导入`AliasField`失败? --- ' + str(e))

