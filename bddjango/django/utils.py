"""
依赖django的功能函数
"""

from .. import pure

import math
import pandas as pd

from django.core.paginator import Paginator
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from functools import wraps
from django.db import connection
from django.db.models import Q, F
from django.db.models import QuerySet
from django.db.models import Max
from django.conf import settings
from warnings import warn
from django.core.management.color import no_style
from django.db import connection

from rest_framework.renderers import JSONRenderer
from django.forms import model_to_dict
from django.db.models import QuerySet
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin, DestroyModelMixin
from rest_framework import status
from django.db.models import Model
from rest_framework.exceptions import APIException
from rest_framework.exceptions import ErrorDetail
import re
from django.contrib.contenttypes.models import ContentType
import json
from rest_framework import serializers as s
from django.http.request import QueryDict
from .auth import get_my_api_error, my_api_assert_function
import re
import sys
from .conf import PAGINATION_SETTINGS
from django.db import models as m
from django.db import connection
from copy import deepcopy
# from rest_framework import serializers


def get_list(query_dc, key):
    if isinstance(query_dc, QueryDict):
        ret = query_dc.getlist(key)
    elif isinstance(query_dc, dict):
        ret = query_dc.get(key)
    else:
        raise TypeError('query_dc类型不明!')

    if isinstance(ret, str):
        ret = [ret]

    if ret == ['']:
        ret = []

    return ret


def get_key_from_request_data_or_self_obj(request_data, self_obj, key, get_type=None):
    """
    优先检索request_data是否有key, 其次检索self_obj是否有key这个属性
    :param key: 变量名
    :return:
    """
    query_dc = request_data

    if get_type == 'list':
        value = get_list(query_dc, key)
    elif get_type == 'bool':
        value = query_dc.get(key)
        ret_0 = getattr(self_obj, key) if hasattr(self_obj, key) else None
        ret_1 = pure.convert_query_parameter_to_bool(value) if value else None
        ret = ret_1 if ret_1 is not None else ret_0
        return ret
    else:
        value = query_dc.get(key)

    # 让request携带的数据可以覆盖自身的key值
    ret_0 = getattr(self_obj, key) if hasattr(self_obj, key) else None
    ret = value if value is not None else ret_0
    return ret


def set_query_dc_value(query_dc: (QueryDict, dict), new_dc: dict):
    assert isinstance(query_dc, QueryDict), 'query_dc必须是QueryDict类型!'
    query_dc._mutable = True
    for key, value in new_dc.items():
        ls = value if isinstance(value, (tuple, list)) else [value]
        query_dc.setlist(key, ls)
    query_dc._mutable = False
    return query_dc


def get_ls_a_different_ls_b(a, b, keep_sort=True):
    """
    列表a和列表b的差集a-b, 并保留a列表原顺序
    """
    ret = list(set(a) - set(b))
    if keep_sort:
        ret.sort(key=a.index)
    return ret


def get_field_names_by_model(model_class, field_attr='name', exclude_fields=None):
    """
    获得`model_class.meta`中的字段名属性

    :param model_class: 目标模型
    :param field_attr: 可取[name, verbose_name]
    :param exclude_fields: 要排除的字段       # 差集 --> set(a).difference(set(b)), DRF在Meta中用exclude指定
    :return:
    """
    if isinstance(model_class, m.QuerySet):
        model_class = get_base_model(model_class)
    assert hasattr(model_class, '_meta'), f'model_class没有`_meta`属性? type(model_class): {type(model_class)}'

    fields = model_class._meta.fields
    field_names = [getattr(field, field_attr) for field in fields]

    if exclude_fields:
        assert isinstance(exclude_fields, (list, tuple)), '`exclude_fields`必须为list或tuple类型!'
        field_names = get_ls_a_different_ls_b(field_names, exclude_fields, keep_sort=True)
    return field_names


def get_base_serializer(base_model, base_fields='__all__', auto_generate_annotate_fields=None):
    """
    生成一个基础序列化器

    :param base_model: queryset或者base_model
    :param base_fields: 想要返回的字段
    :param auto_generate_annotate_fields: 指定将自动生成的annotate的字段, 为[True, '__all__']时自动替换为base_fields
    :return:
    """
    base_model = get_base_model(base_model)
    field_names = get_field_names_by_model(base_model)
    if base_fields != '__all__' and auto_generate_annotate_fields is None:
        if len(set(base_fields) - set(field_names)):
            auto_generate_annotate_fields = True

    if auto_generate_annotate_fields is None:
        class BaseSerializer(s.ModelSerializer):
            class Meta:
                model = base_model
                fields = base_fields

        base_serializer = BaseSerializer
        return base_serializer
    else:
        if auto_generate_annotate_fields is True or auto_generate_annotate_fields in ['__all__', ['__all__']]:
            auto_generate_annotate_fields = base_fields
        elif isinstance(auto_generate_annotate_fields, list):
            auto_generate_annotate_fields = auto_generate_annotate_fields + field_names
        else:
            raise ValueError(f"auto_generate_annotate_fields[{auto_generate_annotate_fields}]取值错误!")

        # --- 这里要把queryset里有, 但model.fields里没有的字段在serializers时自动加上
        new_dc_ls = []
        new_func_ls = []
        for field in auto_generate_annotate_fields:
            if field not in field_names and field not in '__all__':
                # 指定方法字段 SerializerMethodField 后, 再增加 get_field_function.
                field_method = s.SerializerMethodField()
                new_func_name = f'get_{field}'

                def get_field_value(self, obj):
                    ret = None
                    k_name = getattr(self, '__field_name__')
                    if hasattr(obj, k_name):
                        ret = getattr(obj, k_name)
                    elif isinstance(obj, dict) and k_name in obj:
                        ret = obj.get(k_name)
                    else:
                        msg = f'自动生成的[{k_name}]字段值为空! --- from get_base_serializer'
                        warn(msg)
                    return ret

                new_func_cls = {
                    '__field_name__': field,
                    new_func_name: get_field_value,
                }
                new_func_cls = type("new_func_cls", (object,), new_func_cls)
                new_func = getattr(new_func_cls(), new_func_name)

                new_dc_i = {
                    field: field_method,
                }
                new_func_i = {
                    new_func_name: new_func,
                }
                new_dc_ls.append(new_dc_i)
                new_func_ls.append(new_func_i)

        # --- 生成新序列化器base_serializer
        meta_dc = {
            'model': base_model,
            'fields': base_fields
        }
        Meta = type("Meta", (object,), meta_dc)
        cls_dc = {
            'Meta': Meta,
        }
        for i in range(len(new_dc_ls)):
            cls_dc.update(new_dc_ls[i])
            cls_dc.update(new_func_ls[i])
        base_serializer = type("BaseSerializer", (s.ModelSerializer,), cls_dc)
        return base_serializer


def judge_is_obj_level_of_request(request):
    """
    判断本次访问是否为obj对象级, 否则就是model模型级
    """
    if 'pk' in request._request.resolver_match.kwargs:
        return True
    else:
        return False


def conv_queryset_ls_to_serialzer_ls(qs_ls: list):
    """
    qs_ls: 多个queryset数据的序列化, 手动转化为dc_ls
    """
    dc_ls = []
    if not qs_ls:
        return dc_ls

    q = qs_ls[0]
    if not isinstance(q, dict):
        q = model_to_dict(q)
    kname_ls = list(q.keys())

    dc_ls = []
    for q in qs_ls:
        # print(q)
        for kname_i in kname_ls:
            dc = {
                kname_i: getattr(q, kname_i)
            }
            dc_ls.append(dc)
    return dc_ls


def get_field_type_in_db(model, field_name):
    """根据模型和字段名, 获取这个字段在数据库中对应的类型"""
    tp = model._meta.get_field(field_name).get_internal_type()
    return tp


def convert_db_field_type_to_python_type(tp):
    tp = re.sub(r'\(.*\)', '', tp)      # 删除括号内的内容, 如"CharField(source='more_group.explain') "
    if tp in ['TextField', 'CharField', 'DateField', 'FileField', 'DateTimeField']:
        field_type = 'str'
    elif tp in ['IntegerField', 'AutoField', 'BigAutoField']:
        field_type = 'int'
    elif tp in ['FloatField']:
        field_type = 'float'
    elif tp == 'BooleanField':
        field_type = 'bool'
    elif '=' in tp:
        # 类, 一般返回一个dc_ls类型
        field_type = 'list'
    else:
        field_type = tp
    return field_type


def get_field_type_in_py(model, field_name):
    """根据模型和字段名, 获取这个字段在python中对应的类型"""
    tp = get_field_type_in_db(model, field_name)
    field_type = convert_db_field_type_to_python_type(tp)
    return field_type


def reset_db_sequence(model):
    """重置数据库索引, 避免postgresql在手动导入csv/excel后出错."""
    md = get_base_model(model)
    sequence_sql = connection.ops.sequence_reset_sql(no_style(), [md])
    with connection.cursor() as cursor:
        for sql in sequence_sql:
            cursor.execute(sql)
    cursor.close()


def APIResponse(ret=None, status=200, msg=None):
    if isinstance(ret, Response):
        ret = ret.data
    ret = pure.add_status_and_msg(ret, status=status, msg=msg)
    ret = Response(ret)
    return ret


class Pagination(PageNumberPagination):
    """
    * 默认分页器参数设置

    - page_size: 每页16个
    - page_size_query_param: 前端控制每页数量时使用的参数名, 'page_size'
    - page_query_param: 页码控制参数名"p"
    - max_page_size: 最大1000页
    """
    page_size = int(PAGINATION_SETTINGS.get('page_size'))
    page_size_query_param = PAGINATION_SETTINGS.get('page_size_query_param', 'page_size')
    page_query_param = PAGINATION_SETTINGS.get('page_query_param', 'p')
    max_page_size = int(PAGINATION_SETTINGS.get('max_page_size'))


class StateMsgResultJSONRenderer(JSONRenderer):

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if 'status' not in data and 'msg' not in data:
            if 'detail' in data:
                e = data.pop('detail')

                msg = str(e)
                if data:
                    msg += str(data)

                if isinstance(e, ErrorDetail) and e.code == 'permission_denied':
                    status = 403
                else:
                    print('! ************ 莫名返回格式 StateMsgResultJSONRenderer **************')
                    status = 404
                    try:
                        msg = f"[{str(e.code)}] {msg}"
                    except:
                        pass
                data = {
                    'status': status,
                    'msg': msg,
                    'result': [],
                }
            else:
                pass
        return super(StateMsgResultJSONRenderer, self).render(data, accepted_media_type, renderer_context)


def get_base_model(obj) -> Model:
    """判断是Queryset还是BaseModel"""
    if isinstance(obj, QuerySet):
        return obj.model
    else:
        if isinstance(obj, ContentType):
            base_model = obj.model_class()
            return base_model

        if hasattr(obj, 'objects'):
            # BaseModel
            return obj
        elif hasattr(obj.__class__, 'objects'):
            # 单个obj
            return obj.__class__
        else:
            return obj


def get_base_queryset(obj) -> QuerySet:
    """
    返回所有obj类型的QuerySet
    """
    ret = get_base_model(obj)
    ret = ret.objects.all()
    return ret


def conv_to_queryset(obj) -> QuerySet:
    """
    强制转换为QuerySet
    """
    if not isinstance(obj, QuerySet):
        ret = get_base_model(obj)
        ret = ret.objects.all()
    else:
        ret = obj
    return ret


def paginate_qsls_to_dcls(qsls, serializer, page: int, per_page=16, context=None):
    """
    * 手动分页函数

    - 指定模型的queryset_ls和serializer, 然后按给定的page和per_page参数获取分页后的数据
    """

    page_size = int(per_page)

    if page_size == 0:
        page_dc = {
            "count_items": qsls.count(),
            "total_pages": None,
            "page_size": page_size,
            "p": int(page)
        }
        return [], page_dc

    p = Paginator(qsls, per_page)
    page_dc = {
        "count_items": int(p.count),
        "total_pages": int(p.num_pages),
        "page_size": page_size,
        "p": int(page)
    }

    page_obj = p.get_page(page)

    # --- 处理单个Model和多个Model的情况
    if serializer.__class__.__name__ == 'function':
        try:
            dc_ls = serializer(page_obj, context=context)
        except Exception as e:
            raise Exception(f'--- paginate_qsls_to_dcls错误!!! 2022/2/25, error: {e}')
    else:
        dc_ls = serializer(page_obj, many=True, context=context).data
    return dc_ls, page_dc


def conv_queryset_to_dc_ls(queryset: QuerySet):
    dc_ls = []
    for q in queryset:
        dc_ls.append(q)
    return dc_ls


def order_qs_ls_by_id(qs_ls, sort_by='id', ascending=True):
    df = pd.DataFrame(qs_ls)
    if df.empty:
        return []
    df = df.sort_values(by=sort_by, ascending=ascending)

    cols = df.columns
    dc_ls = []
    for i, row in df.iterrows():
        dc = {}
        for j in range(len(cols)):
            _dc = {cols[j]: row.get(cols[j])}
            dc.update(_dc)
        dc_ls.append(dc)
    return dc_ls


def order_by_order_type_ls(queryset, order_type_ls) -> QuerySet:
    """
    根据传入的order_type_ls参数, 对queryset进行排序.

    若order_type_ls包含__None__, 则清空queryset的排序规则.
    """
    if '__None__' in order_type_ls:
        ret = queryset.order_by()
    elif order_type_ls is None or isinstance(order_type_ls, str):
        ret = order_by_order_type(queryset, order_type_ls)
    else:
        ls = []
        for order_type in order_type_ls:
            if order_type:
                if order_type.startswith('-'):
                    order_type1 = order_type[1:]
                    ls.append(F(order_type1).desc(nulls_last=True))
                else:
                    ls.append(F(order_type).asc(nulls_first=True))
        ret = queryset.order_by(*ls)
    return ret


def order_by_order_type(queryset, order_type=None):
    ret = queryset
    if order_type:
        if order_type.startswith('-'):
            order_type1 = order_type[1:]
            ret = queryset.order_by(F(order_type1).desc(nulls_last=True))
        else:
            ret = queryset.order_by(F(order_type).asc(nulls_first=True))

    return ret


def api_decorator(func):
    """
    * API装饰器

    - 如果运行出错, 将格式化输出错误的信息, 并返回给前端, 而不会报错.
    - 自动处理postgresql中idle状态connection过多的情况
    """
    @wraps(func)
    def wrapped_function(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print('--- API Error! ---')
            print(e)
            msg = f'Error! {str(e)}'

            e_str = str(e)
            if 'client' in e_str:
                msg += '!!!!!! 可能出现postgresql的idle链接状况???'
                print(msg)
                # --- postgres的idle链接需要解决, 关闭旧链接(以下使用), 或单线程运行`manage.py runserver --nothreading`
                from django.db import close_old_connections
                from django.db import connection
                close_old_connections()
                with connection.cursor() as cursor:
                    sql = "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle'"
                    cursor.execute(sql)
                    row = cursor.fetchall()
                    print(sql)
                    print(row)
            my_api_assert_function(False, msg=msg, status='404')
    return wrapped_function


def get_model_max_id_in_db(model):
    """
    仅适用于postgresql, mysql直接忽略就行.
    """
    meta = model._meta
    if not callable(model):
        model = type(model)
    ordering = meta.ordering

    assert sum([1 if f.name == 'id' and f.primary_key is True else 0 for f in meta.fields]), "Model的主键必须是id!"

    if ordering:
        if ordering[0] == '-id':
            obj = model.objects.first()
            max_id = obj.id if obj else 0
            ret = max_id + 1
            return ret
        if ordering[0] == 'id':
            obj = model.objects.last()
            max_id = obj.id if obj else 0
            ret = max_id + 1
            return ret
    qs = model.objects.all()
    max_id = qs.aggregate(max_id=Max('id')).get('max_id')  if qs.count() else 0
    ret = max_id + 1
    return ret


def old_get_model_max_id_in_db(model):
    meta = model._meta

    assert sum([1 if f.name == 'id' and f.primary_key is True else 0 for f in meta.fields]), "Model的主键必须是id!"

    cursor = connection.cursor()
    # db_prefix = meta.__str__().split('.')[0]

    # --- 先尝试创建id_seq
    id_seq = f"{meta.app_label}_{meta.db_table}_id_seq"

    try:
        sql = f"""CREATE SEQUENCE IF NOT EXISTS {id_seq}"""
        cursor.execute(sql)
    except Exception as e:
        # mysql不执行本函数也能正常运行
        print(e)
        print('不是PostgreSQL无法运行CREATE SEQUENCE语句! 请确认数据库类型!')

    # --- 找出最大的id
    sql = f"""select setval('{id_seq}', (select max(id) from "{meta.db_table}")+1);"""
    print('---', sql)
    # sql = '(select max(id) from  "{meta.db_table}")'
    # print('sql---', sql)
    cursor.execute(sql)
    row = cursor.fetchall()
    curr_id = row[0][0]
    ret = 0 if curr_id is None else curr_id
    cursor.close()
    return ret


def get_abs_order_type_ls(order_type_ls):
    if isinstance(order_type_ls, str):
        order_type_ls = [order_type_ls]
    ret = [re.sub(r'^-', '', field_name) for field_name in order_type_ls]
    return ret


def get_executable_sql(queryset):
    """
    输入queryset, 获得可直接执行的sql语句
    """
    cursor = connection.cursor()
    sql, params = queryset.query.sql_with_params()
    prefix = 'EXPLAIN '
    cursor.execute(prefix + sql, params)
    sql: str = cursor.db.ops.last_executed_query(cursor, sql, params)
    sql = sql[len(prefix):]
    cursor.close()
    return sql


def get_MySubQuery(my_model, field_name, function_name, output_field=m.IntegerField, alias=None):
    """
    # 获取子查询

    ## 简介
    - 主要用在进行`qs_ls.all().order_by().order_by(field_name).distinct(field_name)`后, 再进行`annotate`操作.
    - 普通的`m.SubQuery`操作将在`distinct`后的`annotate`中报错!

    ## 参考
    - [django文档_1](https://django-orm-cookbook-zh-cn.readthedocs.io/zh_CN/latest/subquery.html)
    - [django文档_2](https://docs.djangoproject.com/zh-hans/4.0/ref/models/expressions/)

    :param my_model: 指定模型, 用以获取模型基本属性`meta`. 若为空, 则认为是annotate字段, 使用默认的field_name.
    :param field_name: 用来进行计算的字段名
    :param function_name: 要在数据库中调用的函数名
    :param output_field: 使用Query计算后, 输出的字段类型
    :param alias: 计算后储存结果变量名, 默认为`tmp`
    :return: 子查询类`MySubQuery`

    ## eg:
    SQCount = get_MySubQuery(my_model=classification_qs_ls_0, field_name=foreign_key_name, function_name='Count', output_field=m.IntegerField)
    classification_qs_ls = classification_qs_ls_0.annotate(
        # 每个学科有多少种
        count=SQCount(
            classification_qs_ls_0.filter(**{key: m.OuterRef(key)})
        ),
    )
    """
    base_model = get_base_model(my_model)
    meta = base_model._meta

    field_names = [field.name for field in meta.fields]
    db_column_names = [field.db_column if field.db_column else field.name for field in meta.fields]
    field_dc = dict(zip(field_names, db_column_names))
    db_column_name = field_dc.get(field_name)  # 获取字段在db中的列名
    db_column_name = db_column_name if db_column_name else field_name       # 没有的话, 就用默认field_name

    alias = 'tmp' if not alias else alias
    my_template = f"(SELECT {function_name}({db_column_name}) FROM (%(subquery)s) {alias})"
    my_output_field = output_field

    class MySubQuery(m.Subquery):
        template = my_template
        output_field = my_output_field() if isinstance(my_output_field, type) else my_output_field

    return MySubQuery


def get_obj_by_content_type(obj_id, model_name, app_label):
    ct_qs_ls = ContentType.objects.filter(app_label=app_label, model=model_name)
    assert ct_qs_ls.count() == 1, f'ContentType数量不为1! current_value: {ct_qs_ls.count()}'
    ct_qs_i = ct_qs_ls[0]
    base_model = ct_qs_i.model_class()
    obj = base_model.objects.get(id=obj_id)
    return obj


def get_QS_by_dc(dc, add_type):
    """
    根据dc返回QS
    :param dc: 过滤条件
    :param add_type: 合并逻辑
    :return: QS
    """
    QS = Q()
    for k, v in dc.items():
        d = {k: v}
        QS.add(Q(**d), add_type)
    return QS


def get_model_verbose_name_dc():
    """
    获得model_verbose_name对应的ContentType的id
    """
    ct_qs_ls = ContentType.objects.all()
    dc = {}
    for ct_qs_i in ct_qs_ls:
        base_model = ct_qs_i.model_class()
        if base_model is not None:
            k = base_model._meta.verbose_name
            # v = ct_qs_i.model
            v = ct_qs_i
            dc.update({k: v})
    return dc


def get_user_ip(request):
    context = request.parser_context
    if 'HTTP_X_FORWARDED_FOR' in context["request"].META:
        user_ip = context["request"].META['HTTP_X_FORWARDED_FOR']
    else:
        user_ip = context["request"].META['REMOTE_ADDR']
    return user_ip


def update_none_to_zero_by_field_name(qs_ls, field_name):
    """
    将qs_ls中field_name字段的None改为0
    """
    filter_dc = {
        f'{field_name}__isnull': True
    }
    update_dc = {
        field_name: 0
    }
    qs_ls.filter(**filter_dc).update(**update_dc)


def get_df_by_freq_and_year(
        queryset,
        frequency_cname=None,
        aggregate_method_name='Sum',
        output_col_name=None,
        year_field_name='year',
        complete_year_ls=False,
        year_range_ls=None,
):
    """
    获取加权的年份分布图

    * 这个比较快

    - aggregate_method_name, frequency_cname: 用来aggregate的方法和字段
    - complete_year_ls: 补全中间年份
    - output_col_name: 输出列名
    - year_field_name: 年份字段名
    """
    year_qsv_ls = queryset.values(year_field_name).distinct(year_field_name).order_by(year_field_name)
    year_ls = [dc.get(year_field_name) for dc in year_qsv_ls]
    assert hasattr(m, aggregate_method_name), f'django.db.models不存在[{aggregate_method_name}]方法!'
    aggregate_method = getattr(m, aggregate_method_name)

    output_col_name = output_col_name if output_col_name  else frequency_cname

    if complete_year_ls:
        if year_range_ls:
            year_min, year_max = year_range_ls
        else:
            year_min, year_max = min(year_ls), max(year_ls)
        year_range = list(range(year_min, year_max + 1))
    else:
        year_range = year_ls

    year_distribution_dc_ls = []
    for year in year_range:
        aggregate_dc = {'tmp': aggregate_method(frequency_cname)}
        value = queryset.filter(year=year).aggregate(**aggregate_dc)
        value = 0 if value is None or value.get('tmp') is None else value.get('tmp')

        year_distribution_dc = {
            year_field_name: year,
            output_col_name: value,
        }
        year_distribution_dc_ls.append(year_distribution_dc)
    return year_distribution_dc_ls


def judge_db_is_migrating():
    if 'makemigrations' in sys.argv or 'migrate' in sys.argv:
        return True
    else:
        return False


def get_total_occurrence_times_by_keywords(total_qs_ls, search_field_ls, keywords, get_frequence=False):
    """
    统计keywords在qs_ls的search_field_ls中是否出现

    :param total_qs_ls: 用来统计的queryset
    :param search_field_ls: 要匹配的字段
    :param kw: 用来检索的关键词
    :param get_frequence: 是否精确计算kw在字段中出现的次数
    :return: queryset, 且annotate出现次数, 存在`total_occurrence_times`字段中
    """
    from django.db.models import functions

    my_api_assert_function(isinstance(keywords, list), 'keywords的类型必须为list!')
    search_dc = {}
    occurrence_times_ls = []

    for k in range(len(keywords)):
        kw = keywords[k]
        kw_l = len(kw)
        for sf_i in search_field_ls:
            if get_frequence:
                k_name = f'k{k}_{sf_i}_occurrence_times'
                dc = {
                    k_name: (functions.Length(sf_i) - functions.Length(
                        functions.Replace(sf_i, m.Value(kw), m.Value('')))) / kw_l  # 出现次数
                }
            else:
                k_name = f'k{k}_in_{sf_i}'
                dc = {
                    k_name: m.Exists(total_qs_ls.filter(id=m.OuterRef('id')).filter(**{f'{sf_i}__contains': kw})),   # 判断是否在title中
                }
            occurrence_times_ls.append(k_name)
            search_dc.update(dc)
    res_qs_ls: m.QuerySet = total_qs_ls.annotate(**search_dc)
    # show_ls(res_qs_ls.values(*(['id'] + search_field_ls + list(search_dc.keys())))[:3])

    f_ls = 0
    for i in occurrence_times_ls:
        if get_frequence:
            f_ls += F(i)
        else:
            f_ls += m.Case(
                m.When(**{i: True}, then=m.Value(1)),
                default=0,
                output_field=m.IntegerField()
            )

    res_qs_ls = res_qs_ls.annotate(**{'total_occurrence_times': f_ls})
    ret = res_qs_ls
    return ret


