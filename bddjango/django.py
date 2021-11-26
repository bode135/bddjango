"""
依赖django的功能函数
"""

from . import pure

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


from django.forms import model_to_dict
from django.db.models import QuerySet
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin, DestroyModelMixin
from rest_framework import status
from django.db.models import Model


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
    if tp in ['TextField', 'CharField', 'DateField', 'FileField', 'DateTimeField']:
        field_type = 'str'
    elif tp in ['IntegerField', 'AutoField', 'BigAutoField']:
        field_type = 'int'
    elif tp in ['FloatField']:
        field_type = 'float'
    elif tp == 'BooleanField':
        field_type = 'bool'
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


def APIResponse(ret, status=200, msg=None):
    if isinstance(ret, Response):
        ret = ret.data
    ret = pure.add_status_and_msg(ret, status=status, msg=msg)
    ret = Response(ret)
    return ret


# --- 默认分页器参数设置 PAGINATION_SETTINGS
PAGINATION_SETTINGS = {
    'page_size': 16,       # 每页16个
    'page_size_query_param': 'page_size',       # 前端控制每页数量时使用的参数名, 'page_size'
    'page_query_param': 'p',        # 页码控制参数名"p"
    'max_page_size': 1000,      # 最大1000页
}

if hasattr(settings, 'PAGINATION_SETTINGS'):
    PAGINATION_SETTINGS.update(settings.PAGINATION_SETTINGS)


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


class BaseListView(ListModelMixin, RetrieveModelMixin, GenericAPIView):
    """
    * API: BaseModel的ListView和RetrieveView接口

    - 测试接口:
        - List:
            GET /api/index/BaseList/?order_type=-id&page_size=4&p=1
        - Retrieve:
            GET /api/index/BaseList/5/
    """

    pagination_class = Pagination
    filter_fields = []      # 精确检索的过滤字段, 如果过滤条件复杂的话, 建议重写
    order_type_ls = []
    distinct_field_ls = []

    serializer_class = None
    retrieve_serializer_class = None       # retrieve对应的serializer_class
    list_serializer_class = None       # list对应的serializer_class
    retrieve_filter_field = None

    method = None       # 中间变量, 记录请求是什么类型, list/retrieve等
    _tmp = None      # 无意义, 用来处理数据

    def get(self, request: Request, *args, **kwargs):
        """
        - 如果request携带pk参数, 则进行Retrieve操作, 否则进行List操作.

        - BaseList的默认get请求参数(仅在List操作时生效)
            - page_size: 分页器每页数量, 前端用来控制数据每页展示的数量, 在Pagination类中设置.
            - p: 第p页.
            - order_type: 排序字段, 如"id"和"-id".
        """
        if kwargs.get('pk'):
            self.method = 'retrieve'
            ret, status, msg = self.get_retrieve_ret(request, *args, **kwargs)
        else:
            self.method = 'list'
            ret, status, msg = self.get_list_ret(request, *args, **kwargs)
        return APIResponse(ret, status=status, msg=msg)

    def get_serializer_class(self):
        if self.method == 'retrieve':
            self.serializer_class = self.retrieve_serializer_class or self.serializer_class
        elif self.method == 'list':
            self.serializer_class = self.list_serializer_class or self.serializer_class
        else:
            self.serializer_class = self.retrieve_serializer_class or self.serializer_class or self.list_serializer_class

        assert self.serializer_class, '属性serializer_class不能为空!'
        return self.serializer_class

    def get_retrieve_ret(self, request: Request, *args, **kwargs):
        """
        Retrieve操作

        - pk必须在`url.py::urlpatterns`中设置, 如: path('BaseList/<str:pk>/', views.BaseList.as_view())
        """
        status = 200
        msg = 'ok'

        try:
            ret = self.retrieve(request)
        except Exception as e:
            # 没找到的情况, 404 Not Found
            ret = None
            status = 404
            msg = str(e)
        return ret, status, msg

    def get_object(self):
        """retrieve时, object的获取"""
        retrieve_filter_field = self.retrieve_filter_field if self.retrieve_filter_field else 'id'

        queryset = self.filter_queryset(self.get_queryset())
        pk = self.request.parser_context.get('kwargs').get('pk')
        queryset = get_base_model(queryset).objects.all()

        cmd = f'self._tmp=Q({retrieve_filter_field}={pk})'
        exec (cmd)
        queryset = queryset.filter(self._tmp)
        assert queryset.count() == 1, f'Error! 查询结果的数量应该等于1, 然而实际等于{queryset.count()}.'
        obj = queryset[0]
        self.check_object_permissions(self.request, obj)
        return obj

    def get_list_ret(self, request: Request, *args, **kwargs):
        """
        List操作
        """
        status = 200
        msg = 'ok'

        # --- 得到list方法的queryset
        self.queryset = self.get_list_queryset()

        # --- 根据ordering参数, 获得排序后的queryset
        self.queryset = self.get_ordered_queryset()

        # --- 获取返回数据(转化为特定格式)
        try:
            ret = self.list(request)
        except Exception as e:
            # 页码无效的情况, 404 Not Found
            ret = None
            status = 404
            msg = str(e)
        return ret, status, msg

    def get_ordered_queryset(self):
        """
        按order_type_ls指定的字段排序
        """
        query_dc = self.request.query_params

        order_type_ls = query_dc.getlist('order_type_ls') if query_dc.getlist('order_type_ls') else self.order_type_ls
        if not order_type_ls:
            # 旧版本可能用的order_type, 尝试赋值
            order_type = query_dc.getlist('order_type')
            if order_type:
                order_type_ls = order_type
        if order_type_ls:
            try:
                self.queryset = order_by_order_type_ls(self.queryset, order_type_ls)
            except ValueError as e:
                msg = f'参数order_type_ls指定的排序字段[{order_type_ls}]排序失败! 更多信息: {str(e)}'
                raise ValueError(msg)

        # distinct操作
        distinct_field_ls = self.request.query_params.getlist('distinct_field_ls') if self.request.query_params.getlist('distinct_field_ls') else self.distinct_field_ls
        if distinct_field_ls:
            assert isinstance(distinct_field_ls, (list, tuple)), 'distinct_field_ls因为list或者tuple!'
            self.queryset = self.queryset.distinct(*distinct_field_ls)

        return self.queryset

    def get_list_queryset(self):
        """
        得到queryset, 仅对list方法生效
        """
        self.queryset = self.get_queryset()
        if not isinstance(self.queryset, QuerySet):
            self.queryset = self.queryset.objects.all()
        self.run_list_filter()
        return self.queryset

    def run_list_filter(self):
        """
        返回用self.filter_fields过滤后的queryset列表
        """
        if self.queryset.count():
            """
            过滤字段filter_fields
            """
            query_dc = self.request.query_params

            meta = get_base_model(self.queryset).objects.first()._meta
            field_names = [field.name for field in meta.fields]
            self.queryset = self.get_queryset()

            if self.queryset.count():
                qs_i = self.queryset[0]
                # 可能用annotate增加了注释字段, 所以要处理一下, 避免过滤出错
                if hasattr(qs_i, 'keys') and len(qs_i.keys()) > len(field_names):
                    field_names = list(qs_i.keys())

            for fn in field_names:
                if fn in self.filter_fields:
                    if fn in query_dc:
                        value = query_dc.get(fn)
                        if value is not None and value != '':       # 默认为空字符串时, 将不作为过滤条件
                            exec(f"self.queryset = self.queryset.filter(Q({fn}='{value}'))")
        return self.queryset

    def _get_list_queryset(self):       # 兼容问题
        return self.get_list_queryset()

    def list(self, request: Request, *args, **kwargs):
        if self.distinct_field_ls:
            # resp = self.get_serializer_class()(self.queryset, many=True).data
            page_size = self.request.query_params.get('page_size', self.pagination_class.page_size)
            p = self.request.query_params.get('p', 1)
            resp, _ = paginate_qsls_to_dcls(self.queryset, self.get_serializer_class(), page=p, per_page=page_size)
        else:
            resp = super().list(request, *args, **kwargs)
        ret = self._conv_data_format(resp)
        return ret

    def _conv_data_format(self, data: (dict, Response)):
        """
        调整为cnki标准格式
        """
        if isinstance(data, list):
            page_dc = {
                'count_items': len(data),
                'total_pages': 1,
                'page_size': len(data),
                'p': 1,
            }
            results = data
        else:
            if isinstance(data, Response):
                data = data.data

            # 分页信息
            count = data.get('count')
            page_size = self.request.query_params.get('page_size', self.pagination_class.page_size)
            p = self.request.query_params.get('p', 1)
            total = math.ceil(count / int(page_size))

            page_dc = {
                'count_items': count,
                'total_pages': total,
                'page_size': page_size,
                'p': p,
            }

            results = data.get('results')

        ret = {
            'page_dc': page_dc,
            'data': results,
        }
        return ret


class BaseList(BaseListView):     # 向下兼容, 返回格式调整, 重写_conv_data_format.
    def _conv_data_format(self, data: (dict, Response)):
        if isinstance(data, Response):
            data = data.data

            # 分页信息
        count = data.get('count')
        page_size = self.request.query_params.get('page_size', self.pagination_class.page_size)
        p = self.request.query_params.get('p', 1)
        total = math.ceil(count / int(page_size))
        page_dc = {
            'count': count,
            'total': total,
            'page_size': page_size,
            'p': p,
        }

        results = data.get('results')

        ret = {
            'page_dc': page_dc,
            'results': results,
        }
        return ret


def get_base_model(obj) -> Model:
    """判断是Queryset还是BaseModel"""
    if isinstance(obj, QuerySet):
        return obj.model
    else:
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


def paginate_qsls_to_dcls(qsls, serializer, page: int, per_page=16):
    """
    * 手动分页函数

    - 指定模型的queryset_ls和serializer, 然后按给定的page和per_page参数获取分页后的数据
    """

    p = Paginator(qsls, per_page)
    page_obj = p.get_page(page)
    page_dc = {
        'num_pages': p.num_pages,
        'count_objects': p.count,
        'current_page_number': page_obj.number,
    }

    # --- 处理单个Model和多个Model的情况
    if serializer.__class__.__name__ == 'function':
        dc_ls = serializer(page_obj)
    else:
        dc_ls = serializer(page_obj, many=True).data
    return dc_ls, page_dc


def conv_queryset_to_dc_ls(queryset: QuerySet):
    dc_ls = []
    for q in queryset:
        dc_ls.append(q)
    return dc_ls


def order_qs_ls_by_id(qs_ls, sort_by='id'):
    df = pd.DataFrame(qs_ls).sort_values(by=sort_by)

    cols = df.columns
    dc_ls = []
    for i, row in df.iterrows():
        dc = {
            cols[0]: row.get(cols[0]),
            cols[1]: row.get(cols[1]),
        }
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
    """
    @wraps(func)
    def wrapped_function(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print('--- API Error! ---')
            print(e)
            return APIResponse(None, status=404, msg=f'Error! {str(e)}')
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


from .mixins import MyCreateModelMixin, MyUpdateModelMixin, MyDestroyModelMixin


class CompleteModelView(BaseListView, MyCreateModelMixin, MyUpdateModelMixin, MyDestroyModelMixin):
    """
    * 一个模型的增删改查全套接口

    - 可在post方法中使用post_type指定操作类型.

    > 以下方法分别对应同一个url下的: 增, 删, 改, 查.

    - POST
        - 创建新数据
    - DELETE
        - 删除数据, 需指定id
    - PUT
        - 修改数据, 需指定id
    - GET
        - 查询列表页`GET url/`
        - 查询详情页, 需指定id.
          - 如: `GET url/id/`
    """
    post_type_ls = ["create", "delete", "retrieve", "update"]       # post请求方法
    create_unique = True        # 创建时是否允许重复

    def post(self, request, *args, **kwargs):
        """增"""
        post_type = request.data.get('post_type', 'create')
        assert not post_type or post_type in self.post_type_ls, f"操作类型post_type指定错误! 取值范围: {self.post_type_ls}"

        if post_type == 'create':
            return self.create(request, *args, **kwargs)
        elif post_type == 'delete':
            return self.destroy(request, *args, **kwargs)
        elif post_type == 'retrieve':
            return self.get(request, *args, **kwargs)
        elif post_type == 'update':
            return self.put(request, *args, **kwargs)
        else:
            return APIResponse(None, status=404, msg='请指定post操作类型, [create, update, delete]?')

    def delete(self, request, *args, **kwargs):
        """删"""
        return self.destroy(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """改"""
        return self.update(request, *args, **kwargs)


class DecoratorBaseListView(BaseListView):
    @api_decorator
    def get(self, request, *args, **kwargs):
        return super().get(*args, **kwargs)


class DecoratorCompleteModelView(CompleteModelView):
    """
    全部用api_decorator装饰
    """

    @api_decorator
    def get(self, request, *args, **kwargs):
        return super().get(*args, **kwargs)

    @api_decorator
    def post(self, *args, **kwargs):
        return super().post(*args, **kwargs)

    @api_decorator
    def put(self, request, *args, **kwargs):
        return super().put(*args, **kwargs)

    @api_decorator
    def delete(self, request, *args, **kwargs):
        return super().delete(*args, **kwargs)


from django.db import connection


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


from django.db import models as m


def get_MySubQuery(my_model, field_name, function_name, output_field=m.IntegerField, alias=None):
    base_model = get_base_model(my_model)
    meta = base_model._meta

    field_names = [field.name for field in meta.fields]
    db_column_names = [field.db_column if field.db_column else field.name for field in meta.fields]
    field_dc = dict(zip(field_names, db_column_names))
    db_column_name = field_dc.get(field_name)  # 获取字段在db中的列名

    alias = 'tmp' if not alias else alias
    my_template = f"(SELECT {function_name}({db_column_name}) FROM (%(subquery)s) {alias})"
    my_output_field = output_field

    class MySubQuery(m.Subquery):
        template = my_template
        output_field = my_output_field()

    return MySubQuery


