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


def get_list(query_dc, key):
    if isinstance(query_dc, QueryDict):
        ret = query_dc.getlist(key)
    elif isinstance(query_dc, dict):
        ret = query_dc.get(key)
    else:
        raise TypeError('query_dc类型不明!')
    return ret


def get_base_serializer(base_model, base_fields='__all__'):
    """
    生成一个基础序列化器

    :param base_model: queryset或者base_model
    :param base_fields: 字段
    :return:
    """
    base_model = get_base_model(base_model)

    class BaseSerializer(s.ModelSerializer):
        class Meta:
            model = base_model
            fields = base_fields
    base_serializer = BaseSerializer
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
                data = {
                    'status': status,
                    'msg': msg,
                    'result': [],
                }
            else:
                pass
        return super(StateMsgResultJSONRenderer, self).render(data, accepted_media_type, renderer_context)


class BaseListView(ListModelMixin, RetrieveModelMixin, GenericAPIView):
    """
    * API: BaseModel的ListView和RetrieveView接口

    - 测试接口:
        - List:
            GET /api/index/BaseList/?order_type=-id&page_size=4&p=1
        - Retrieve:
            GET /api/index/BaseList/5/
    """
    
    _name = 'BaseListView'
    
    renderer_classes = (StateMsgResultJSONRenderer,)

    pagination_class = Pagination

    filter_fields = []       # ['__all__']过滤所有. 精确检索的过滤字段, 如果过滤条件复杂的话, 建议重写

    order_type_ls = []
    distinct_field_ls = []

    serializer_class = None
    auto_generate_serializer_class = False
    base_fields = '__all__'     # 当auto_generate_serializer_class为True时, 将自动生成序列化器, 然后根据base_fields返回字段

    retrieve_serializer_class = None       # retrieve对应的serializer_class
    list_serializer_class = None       # list对应的serializer_class

    retrieve_filter_field = None        # 详情页的查询字段名, 默认为 {{url}}/app/view/pk , 无需变动.

    method = None       # 中间变量, 记录请求是什么类型, list/retrieve等
    _tmp = None      # 无意义, 用来处理数据

    _post_type = None   # 用来判断是什么请求类型, 然后判断request_data取哪个
    post_type_ls = ["list", "retrieve", "bulk_list"]  # post请求方法
    create_unique = True  # 创建时是否允许重复

    def get(self, request: Request, *args, **kwargs):
        """
        - 如果request携带pk参数, 则进行Retrieve操作, 否则进行List操作.

        - BaseList的默认get请求参数(仅在List操作时生效)
            - page_size: 分页器每页数量, 前端用来控制数据每页展示的数量, 在Pagination类中设置.
            - p: 第p页.
            - order_type_ls: 排序字段, 如"id"和"-id".
        """
        if kwargs.get('pk'):
            self.method = 'retrieve'
            ret, status, msg = self.get_retrieve_ret(request, *args, **kwargs)
        else:
            self.method = 'list'
            ret, status, msg = self.get_list_ret(request, *args, **kwargs)
        return APIResponse(ret, status=status, msg=msg)

    def bulk_list(self, request, *args, **kwargs):
        """
        根据id批量删除
        """
        query_dc = self.get_request_data()

        id_ls = get_list(query_dc, 'id_ls')
        self.method = query_dc.get('http_method', 'retrieve')       # 优先返回retrieve详情数据

        my_api_assert_function(id_ls, msg=f'id_ls[{id_ls}]不能为空!!!')
        my_api_assert_function(isinstance(id_ls, list), msg=f'id_ls[{id_ls}]应为list类型, 不应为{id_ls.__class__.__name__}类型!!')

        base_model = get_base_model(self.queryset)
        qs_ls = base_model.objects.filter(id__in=id_ls)
        self.queryset = qs_ls

        qs_ls = self.get_ordered_queryset()

        page_size = query_dc.get('page_size', self.pagination_class.page_size)
        p = query_dc.get('p', 1)
        data, page_dc = paginate_qsls_to_dcls(qs_ls, self.get_serializer_class(), page=p, per_page=page_size)
        ret = {
            'page_dc': page_dc,
            'data': data
        }
        return APIResponse(ret)

    def post(self, request, *args, **kwargs):
        """用post方法来跳转"""
        post_type = request.data.get('post_type', 'list')
        self._post_type = post_type
        my_api_assert_function(not post_type or post_type in self.post_type_ls, f"操作类型post_type指定错误! 取值范围: {self.post_type_ls}")

        if post_type in ['list', 'retrieve']:
            return self.get(request, *args, **kwargs)
        elif post_type == 'bulk_list':
            return self.bulk_list(request, *args, **kwargs)
        else:
            return APIResponse(None, status=404, msg=f'请指定post操作类型, 取值范围: {self.post_type_ls}?')

    def get_serializer_class(self):
        if self.method == 'retrieve':
            self.serializer_class = self.retrieve_serializer_class or self.serializer_class
        elif self.method == 'list':
            self.serializer_class = self.list_serializer_class or self.serializer_class
        else:
            self.serializer_class = self.retrieve_serializer_class or self.serializer_class or self.list_serializer_class

        if self.auto_generate_serializer_class and self.serializer_class is None:
            self.serializer_class = get_base_serializer(self.queryset, base_fields=self.base_fields)

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
            # 这里有坑, 因为有可能返回的是已经自定义好了的APIException, 例如权限不足错误.
            if not isinstance(e, APIException):
                # 没找到的情况, 404 Not Found
                ret = None
                status = 404
                msg = str(e)
                # msg = 'RetrieveError__' + str(e)
            else:
                raise e

        return ret, status, msg

    def get_object(self):
        """retrieve时, object的获取"""
        retrieve_filter_field = self.retrieve_filter_field if self.retrieve_filter_field else 'id'

        queryset = self.filter_queryset(self.get_queryset())
        pk = self.request.parser_context.get('kwargs').get('pk')
        queryset = get_base_model(queryset).objects.all()

        cmd = f'self._tmp=Q({retrieve_filter_field}={pk})'
        exec(cmd)

        queryset = queryset.filter(self._tmp)
        assert queryset.count() == 1, f'__{status.HTTP_404_NOT_FOUND}__: Error! 查询结果的数量应该等于1, 然而实际等于{queryset.count()}.'
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

    def get_request_data(self)->dict:
        """
        请求所携带的数据, 除了get方法跳过来的外, 均以请求体body携带的数据request.data优先.
        """
        if not hasattr(self, 'request'):
            return {}

        if self._post_type is None:
            ret = self.request.query_params
        else:
            # ret = self.request.GET or self.request.query_params or self.request.data
            ret = self.request.data or self.request.query_params

        if hasattr(self, '_set_request_data') and getattr(self, '_set_request_data'):
            ret = self._set_request_data
        return ret

    def set_request_data(self, request_data):
        self._set_request_data = request_data

    def get_ordered_queryset(self):
        """
        按order_type_ls指定的字段排序
        """
        query_dc = self.get_request_data()
        order_type_ls = get_list(query_dc, key='order_type_ls') if get_list(query_dc, key='order_type_ls') else self.order_type_ls
        distinct_field_ls = get_list(query_dc, key='distinct_field_ls') if get_list(query_dc, key='distinct_field_ls') else self.distinct_field_ls

        if not order_type_ls:
            # 旧版本可能用的order_type, 尝试赋值
            order_type = get_list(query_dc, key='order_type')
            if order_type:
                order_type_ls = order_type

        if order_type_ls:
            # print('distinct_field_ls', distinct_field_ls, '--- order_type_ls', order_type_ls)
            if distinct_field_ls and distinct_field_ls not in ['__None__', ['__None__']]:
                d_len = len(distinct_field_ls)
                my_api_assert_function(order_type_ls[:d_len] == distinct_field_ls, 'order_type_ls必须包含distinct_field_ls, 且需要将distinct_field_ls置于最前方!')

            try:
                self.queryset = order_by_order_type_ls(self.queryset, order_type_ls)
            except ValueError as e:
                msg = f'参数order_type_ls指定的排序字段[{order_type_ls}]排序失败! 更多信息: {str(e)}'
                raise ValueError(msg)

        # distinct操作
        if distinct_field_ls and distinct_field_ls not in ['__None__', ['__None__']]:
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
            query_dc = self.get_request_data()
            FILTER_ALL_FIELDS = True if self.filter_fields in ['__all__', ['__all__']] else False

            self.queryset = self.get_queryset()
            base_model = get_base_model(self.queryset)
            if base_model.objects.count() == 0:
                return self.queryset

            meta = base_model.objects.first()._meta
            field_names = [field.name for field in meta.fields]
            if self.queryset.count():
                qs_i = self.queryset[0]
                # 可能用annotate增加了注释字段, 所以要处理一下, 避免过滤出错
                if hasattr(qs_i, 'keys') and len(qs_i.keys()) > len(field_names):
                    field_names = list(qs_i.keys())

            for fn in field_names:      # fn: field_name
                if FILTER_ALL_FIELDS or fn in self.filter_fields:
                    if fn in query_dc:
                        value = query_dc.get(fn)
                        if value is not None and value != '':       # 默认为空字符串时, 将不作为过滤条件
                            dc = {fn: value}
                            q = Q(**dc)
                            self.queryset = self.queryset.filter(q)
                            # ss = f"self.queryset = self.queryset.filter(Q({fn}='{value}'))"
                            # exec(f"self.queryset = self.queryset.filter(Q({fn}='{value}'))")
        return self.queryset

    def _get_list_queryset(self):       # 兼容问题
        return self.get_list_queryset()

    def list(self, request: Request, *args, **kwargs):
        query_dc = self.get_request_data()
        page_size = query_dc.get('page_size', self.pagination_class.page_size)
        p = query_dc.get('p', 1)
        resp, page_dc = paginate_qsls_to_dcls(self.queryset, self.get_serializer_class(), page=p, per_page=page_size)
        ret = self._conv_data_format(resp, page_dc)
        return ret

    def _conv_data_format(self, data: (dict, Response), page_dc):
        """
        调整为cnki标准格式
        """

        # if isinstance(data, list):
        #     page_dc = {
        #         'count_items': len(data),
        #         'total_pages': 1,
        #         'page_size': len(data),
        #         'p': 1,
        #     }
        #     results = data
        # else:
        #     if isinstance(data, Response):
        #         data = data.data
        #
        #     # 分页信息
        #     count = data.get('count')
        #     page_size = self.get_request_data().get('page_size', self.pagination_class.page_size)
        #     p = self.get_request_data().get('p', 1)
        #     total = math.ceil(count / int(page_size))
        #
        #     page_dc = {
        #         'count_items': count,
        #         'total_pages': total,
        #         'page_size': page_size,
        #         'p': p,
        #     }
        #
        #     results = data.get('results')

        ret = {
            'page_dc': page_dc,
            'data': data,
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


def paginate_qsls_to_dcls(qsls, serializer, page: int, per_page=16):
    """
    * 手动分页函数

    - 指定模型的queryset_ls和serializer, 然后按给定的page和per_page参数获取分页后的数据
    """

    p = Paginator(qsls, per_page)
    page_obj = p.get_page(page)
    # page_dc = {
    #     'num_pages': p.num_pages,
    #     'count_objects': p.count,
    #     'current_page_number': page_obj.number,
    # }
    page_dc = {
            "count_items": int(p.count),
            "total_pages": int(p.num_pages),
            "page_size": int(per_page),
            "p": int(page)
        },

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
    _name = 'CompleteModelView'

    post_type_ls = ["list", "retrieve", "create", "update", "delete", "bulk_delete", "bulk_update", "bulk_list"]       # post请求方法
    _post_type = None
    create_unique = True        # 创建时是否允许重复

    def post(self, request, *args, **kwargs):
        """增"""
        post_type = request.data.get('post_type', 'create')
        self._post_type = post_type
        my_api_assert_function(not post_type or post_type in self.post_type_ls, f"操作类型post_type指定错误! 取值范围: {self.post_type_ls}")

        if post_type == 'create':
            return self.create(request, *args, **kwargs)
        elif post_type == 'delete':
            return self.destroy(request, *args, **kwargs)
        elif post_type in ['list', 'retrieve']:
            return self.get(request, *args, **kwargs)
        elif post_type == 'update':
            return self.put(request, *args, **kwargs)
        elif post_type == 'bulk_delete':
            return self.bulk_delete(request, *args, **kwargs)
        elif post_type == 'bulk_update':
            return self.bulk_update(request, *args, **kwargs)
        elif post_type == 'bulk_list':
            return self.bulk_list(request, *args, **kwargs)
        else:
            return APIResponse(None, status=404, msg='请指定post操作类型, [create, update, delete]?')

    def delete(self, request, *args, **kwargs):
        """删"""
        return self.destroy(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """改"""
        ret = self.partial_update(request, *args, **kwargs)
        return ret

    def bulk_delete(self, request, *args, **kwargs):
        """
        根据id批量删除
        """
        request_data = self.get_request_data()

        id_ls = get_list(request_data, 'id_ls')
        my_api_assert_function(id_ls, msg=f'id_ls[{id_ls}]不能为空!!!')
        my_api_assert_function(isinstance(id_ls, list), msg=f'id_ls[{id_ls}]应为list类型, 不应为{id_ls.__class__.__name__}类型!!')

        base_model = get_base_model(self.queryset)
        qs_ls = base_model.objects.filter(id__in=id_ls)
        qs_ls.delete()
        return APIResponse()

    def bulk_update(self, request, *args, **kwargs):
        """
        批量更新
        """
        request_data = self.get_request_data()

        id_ls = get_list(request_data, 'id_ls')
        field_dc = request_data.get('field_dc')

        my_api_assert_function(id_ls, msg=f'id_ls[{id_ls}]不能为空!!!')
        my_api_assert_function(isinstance(id_ls, list), msg=f'id_ls[{id_ls}]应为list类型, 不应为{id_ls.__class__.__name__}类型!!')
        my_api_assert_function(field_dc, 'field_dc不能为空!')

        if isinstance(field_dc, str):
            field_dc = json.loads(field_dc)

        # 开始批量更新, 注意只支持2层嵌套.
        foreign_key_field_dc = {}
        original_field_dc = {}
        for k, v in field_dc.items():
            dc = {k: v}
            if '__' in k:
                foreign_key_field_dc.update(dc)
            else:
                original_field_dc.update(dc)

        base_model = get_base_model(self.queryset)
        qs_ls: m.QuerySet = base_model.objects.filter(id__in=id_ls)
        my_api_assert_function(qs_ls.count(), '未找到id_ls对应的数据!')

        qs_i = qs_ls[0]     # 样例数据

        # 先更新原生字段
        qs_ls.update(**original_field_dc)

        # 再依次更新外键字段
        for k, v in foreign_key_field_dc.items():
            fk_model_name, fk_field = k.split('__')
            dc = {fk_field: v}
            foreign_key_obj_i = getattr(qs_i, fk_model_name)
            foreign_key_model = get_base_model(foreign_key_obj_i)
            base_field = getattr(base_model, fk_model_name)
            assert hasattr(base_field, 'related'), '字段不是外键?'
            related = getattr(base_field, 'related')
            foreign_key_field_name = related.field.name
            filter_dc = {
                f'{foreign_key_field_name}__id__in': id_ls
            }
            qs_ls = foreign_key_model.objects.filter(**filter_dc)
            qs_ls.update(**dc)

        # 返回更新后的数据
        qs_ls: m.QuerySet = base_model.objects.filter(id__in=id_ls)
        ret = self.get_serializer_class()(qs_ls, many=True).data
        return APIResponse(ret)


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
    """
    # 获取子查询

    ## 简介
    - 主要用在进行`qs_ls.all().order_by().order_by(field_name).distinct(field_name)`后, 再进行`annotate`操作.
    - 普通的`m.SubQuery`操作将在`distinct`后的`annotate`中报错!

    ## 参考
    - [django文档_1](https://django-orm-cookbook-zh-cn.readthedocs.io/zh_CN/latest/subquery.html)
    - [django文档_2](https://docs.djangoproject.com/zh-hans/4.0/ref/models/expressions/)

    :param my_model: 指定模型, 用以获取模型基本属性`meta`
    :param field_name: 用来进行计算的字段名
    :param function_name: 要在数据库中调用的函数名
    :param output_field: 使用Query计算后, 输出的字段类型
    :param alias: 计算后储存结果变量名, 默认为`tmp`
    :return: 子查询类`MySubQuery`
    """
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
