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
        - excel导入datetime字段时的处理
        - BaseListView中的count替换为exists, 提升性能
        - 修复exists的值取反导致检索全部失效的bug
        - 修复extract_pdf出错的bug: PdfFileReader(pdfFile, strict=False)
        - 返回页码p不能为0的报错信息
        - .adminclass增加注释和使用说明        # 2.4.4
        - bulk_delete增加权限控制        # 2.4.5
        - order_by_order_type_ls修复为[""]的时候出现的bug
        - 页码p的提示更人性化, 改为必须正整数        # 2.4.6
        - 页码p或page_size等于GET_ALL(-999)时, 则返回全部数据
        - admin增加orm检索      # 2.4.7
        - simplrui的admin_class的基类改为`AjaxAdmin`
        - 修复Mixin后置导致的Guadian失效的bug     # 2.4.8
        - 增加_ajax_return_qs_ls, 以便admin中的ajax方法返回qs_ls      # 2.4.9
        - django.utils.get_field_names_by_model增加`field_attr`, 以便获取[name, verbose_name]
        - BaseListView再次简化, 省略get_base_serializer步骤, 只需要list_fields和retrieve_fields即可       # 2.5.0
        - `.django.utils.get_field_names_by_model`增加`exclude_ls`功能, 并按原模型字段顺序排序
        - 完善高级检索功能, AddQS现在支持无限Q_ls的嵌套了     # 2.5.1
        - 过滤条件fn以`__isnull`结尾时, value自动转换为bool类型        # 2.6.0
        - autoWiki兼容list_fields和retrieve_fields
        - adminclass.MyAjaxAdmin导致和simpleui耦合              # 2.6.1
        - admin导入导出功能增加对外键的支持                       # 2.6.2
        - autoWiki模板优化
        - 清除admin导入功能的debug信息                       # 2.6.3
        - adminclass用.filter时增加Q函数支持
        - `get_base_serializer`增加对多层外键字段的支持
        - 解决autoWiki的模板bug(view_class_type引起的请求方式不对)                       # 2.6.4
        - autoWiki优化, 增加`BaseFullTextSearchView`类
        - 增加`baseSearchView.py`, 包含中文全文检索和相关对象推荐
    """
    v = "2.6.4"  # 当前发布: 2.6.4
    return v


try:
    from .django import *
except Exception as e:
    warn('导入django失败? --- ' + str(e))

try:
    from .myFIelds import AliasField  # 这个只能在这里引用, 不然`adminclass`报错
except Exception as e:
    warn('导入`AliasField`失败? --- ' + str(e))
