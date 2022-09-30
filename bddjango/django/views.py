from .utils import *
from rest_framework.views import APIView
from .mixins import MyCreateModelMixin, MyUpdateModelMixin, MyDestroyModelMixin


class BaseListView(ListModelMixin, RetrieveModelMixin, GenericAPIView):
    """
    * API: BaseModel的ListView和RetrieveView接口

    - 测试接口:
        - List:
            GET /api/index/BaseList/?order_type=-id&page_size=4&p=1
        - Retrieve:
            GET /api/index/BaseList/5/
    """

    _name = 'BaseListView'  # 这个在自动生成wiki时要用到

    # renderer_classes = APIView.renderer_classes + [StateMsgResultJSONRenderer]
    pagination_class = Pagination

    filter_fields = '__all__'  # '__all__'过滤所有. 精确检索的过滤字段, 如果过滤条件复杂的话, 建议重写

    order_type_ls = []
    distinct_field_ls = []
    only_get_distinct_field = False  # 仅返回distinct指定的字段

    serializer_class = None
    auto_generate_serializer_class = True
    base_fields = '__all__'  # 当auto_generate_serializer_class为True时, 将自动生成序列化器, 然后根据base_fields返回字段

    list_fields = None
    retrieve_fields = None
    retrieve_serializer_class = None  # retrieve对应的serializer_class
    list_serializer_class = None  # list对应的serializer_class

    retrieve_filter_field = 'pk'  # 详情页的查询字段名, 默认为 {{url}}/app/view/pk , 可由前端指定.

    method = None  # 中间变量, 记录请求是什么类型, list/retrieve等
    _tmp = None  # 无意义, 用来处理数据

    _post_type = None  # 用来判断是什么请求类型, 然后判断request_data取哪个
    post_type_ls = ["list", "retrieve", "bulk_list"]  # post请求方法
    create_unique = True  # 创建时是否允许重复

    convert_to_bool_flag = 'bool__'                       # 将特定格式强制转换为布尔变量, 如 `名字不为空: name__isnull=bool__0`
    negative_flag = '!'                                   # filter_fields 条件取否时使用, 如: `id不等于1: !id=1`

    default_page_size = None        # 默认每页返回的数量
    # add_host_prefix_to_media_url = True                                    # 是否返回文件的时候加上当前域名的prefix

    flat_dc_ls = False      # 是否展平为list然后返回. 只有在返回一个字段的时候才生效.
    add_page_dc = True      # 是否增加`page_dc`

    def __new__(cls, *args, **kwargs):
        ret = super().__new__(cls, *args, **kwargs)

        if cls.list_serializer_class is None and cls.list_fields is not None:
            cls.list_serializer_class = get_base_serializer(cls.queryset, base_fields=cls.list_fields)

        if cls.retrieve_serializer_class is None and cls.retrieve_fields is not None:
            if cls.retrieve_fields == '__all__':
                cls.retrieve_serializer_class = get_base_serializer(
                    cls.queryset,
                    base_fields=cls.retrieve_fields,
                    auto_generate_annotate_fields=cls.list_fields
                )
            else:
                cls.retrieve_serializer_class = get_base_serializer(
                    cls.queryset,
                    base_fields=cls.retrieve_fields,
                )

        if cls.default_page_size is not None and cls.pagination_class is not None:
            if cls.default_page_size == '__all__':
                cls.pagination_class.page_size = -999       # 返回全部
            else:
                cls.pagination_class.page_size = cls.default_page_size

        return ret

    def get(self, request, *args, **kwargs):
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
        self.method = query_dc.get('http_method', 'retrieve')  # 优先返回retrieve详情数据

        my_api_assert_function(id_ls, msg=f'id_ls[{id_ls}]不能为空!!!')
        my_api_assert_function(isinstance(id_ls, list),
                               msg=f'id_ls[{id_ls}]应为list类型, 不应为{id_ls.__class__.__name__}类型!!')

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
        my_api_assert_function(not post_type or post_type in self.post_type_ls,
                               f"操作类型post_type指定错误! 取值范围: {self.post_type_ls}")

        if post_type in ['list', 'retrieve']:
            return self.get(request, *args, **kwargs)
        elif post_type == 'bulk_list':
            return self.bulk_list(request, *args, **kwargs)
        else:
            return APIResponse(None, status=404, msg=f'请指定post操作类型, 取值范围: {self.post_type_ls}?')

    def get_serializer_class(self):
        request_data = self.get_request_data()

        if self.method == 'retrieve':
            ret = self.retrieve_serializer_class or self.serializer_class
        elif self.method == 'list':
            ret = self.list_serializer_class or self.serializer_class
        else:
            ret = self.retrieve_serializer_class or self.serializer_class or self.list_serializer_class

        if (self.auto_generate_serializer_class and ret is None) or request_data.get('base_fields'):
            ret = get_base_serializer(self.queryset, base_fields=self.get_base_fields())

        # --- 仅获取distinct之后的字段
        only_get_distinct_field = self.get_only_get_distinct_field()
        if only_get_distinct_field:
            distinct_field_ls = self.get_distinct_field_ls()
            assert distinct_field_ls, '指定了only_get_distinct_field的同时必须指定distinct_field_ls!'

            if isinstance(distinct_field_ls, str):
                distinct_field_ls = [distinct_field_ls]

            ret = get_base_serializer(self.queryset, distinct_field_ls)
            return ret

        assert ret, '返回的serializer_class不能为空!'
        return ret

    def get_only_get_distinct_field(self):
        key = 'only_get_distinct_field'
        value = self.get_key_from_query_dc_or_self(key)
        ret = pure.convert_query_parameter_to_bool(value)
        return ret

    def get_distinct_field_ls(self):
        key = 'distinct_field_ls'
        ret = self.get_key_from_query_dc_or_self(key, get_type='list')
        return ret

    def get_base_fields(self):
        key = 'base_fields'
        ret = self.get_key_from_query_dc_or_self(key, get_type='list')
        return ret

    def get_retrieve_ret(self, request, *args, **kwargs):
        """
        Retrieve操作

        - pk必须在`url.py::urlpatterns`中设置, 如: path('BaseList/<str:pk>/', views.BaseList.as_view())
        """
        status = 200
        msg = 'ok'

        try:
            ret = self.retrieve(request)
        except Exception as e:
            # # 这里有坑, 因为有可能返回的是已经自定义好了的APIException, 例如权限不足错误.
            # if not isinstance(e, APIException):
            #     # 没找到的情况, 404 Not Found
            #     ret = None
            #     status = 404
            #     msg = str(e)
            #     my_api_assert_function(ret, msg, status)
            # else:
            raise e

        return ret, status, msg

    def get_object(self):
        """retrieve时, object的获取"""
        retrieve_filter_field = self.get_key_from_query_dc_or_self('retrieve_filter_field')

        pk = self.request.parser_context.get('kwargs').get('pk')
        dc = {retrieve_filter_field: pk}
        queryset = self.filter_queryset(self.get_queryset())
        # queryset = queryset.filter(Q(**dc))
        if isinstance(queryset, QuerySet):
            queryset = queryset.filter(Q(**dc))
        else:
            queryset = queryset.objects.filter(Q(**dc))
        # print(get_executable_sql(queryset))

        count = queryset.count()
        if count != 1:
            if count > 1:
                my_api_assert_function(False, f'检索结果不唯一!')
            else:
                my_api_assert_function(False, f'未检索到{dc}对应的内容!')

        obj = queryset[0]
        self.check_object_permissions(self.request, obj)
        return obj

    def get_list_ret(self, request, *args, **kwargs):
        """
        List操作
        """
        status = 200
        msg = 'ok'

        # --- 得到list方法的queryset
        self.queryset = self.get_list_queryset()

        if not isinstance(self.queryset, QuerySet):
            self.queryset = self.queryset.objects.all()

        # --- 根据ordering参数, 获得排序后的queryset
        self.queryset = self.get_ordered_queryset()

        # --- 获取返回数据(转化为特定格式)
        try:
            ret = self.list(request)
        except Exception as e:
            # 页码无效的情况, 404 Not Found
            raise e
            # ret = None
            # my_api_assert_function(ret, f'List error! --- {e}', 404)
            # status = 404
            # msg = str(e)
        return ret, status, msg

    def get_request_data(self) -> dict:
        """
        请求所携带的数据, 除了get方法跳过来的外, 均以请求体body携带的数据request.data优先.
        """
        if not hasattr(self, 'request'):
            return {}

        if self._post_type is None:
            if self.request.method and self.request.method not in ['GET', 'HEAD', 'OPTIONS']:
                ret = self.request.data
            else:
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

        order_type_ls = self.get_key_from_query_dc_or_self('order_type_ls', get_type='list')
        distinct_field_ls = self.get_key_from_query_dc_or_self('distinct_field_ls', get_type='list')

        if not order_type_ls:
            # 旧版本可能用的order_type, 尝试赋值
            order_type = get_list(query_dc, key='order_type')
            if order_type:
                order_type_ls = order_type

        qs_ls = self.queryset

        # distinct操作
        if distinct_field_ls and distinct_field_ls not in ['__None__', ['__None__']]:
            assert isinstance(distinct_field_ls, (list, tuple)), 'distinct_field_ls因为list或者tuple!'
            qs_ls = qs_ls.order_by(*distinct_field_ls).distinct(*distinct_field_ls)  # bug: distinct_field_ls 后的字段无法排序

        # region # --- `order_by`操作
        if not pure.convert_query_parameter_to_bool(order_type_ls):
            base_model = get_base_model(self.queryset)
            ordering = base_model._meta.ordering
            order_type_ls = ordering if ordering else ['pk']

        # 要注意进行distinct之后的排序
        if distinct_field_ls and distinct_field_ls not in ['__None__', ['__None__']]:
            qs_ls = self.queryset.filter(pk__in=qs_ls.values('pk'))

        try:
            qs_ls = order_by_order_type_ls(qs_ls, order_type_ls)
        except ValueError as e:
            msg = f'参数order_type_ls指定的排序字段[{order_type_ls}]排序失败! 更多信息: {str(e)}'
            raise ValueError(msg)
        # endregion

        self.queryset = qs_ls
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
        if self.queryset.exists():
            """
            过滤字段filter_fields
            """
            query_dc = self.get_request_data()
            FILTER_ALL_FIELDS = True if self.filter_fields in ['__all__', ['__all__']] else False

            self.queryset = self.get_queryset()
            base_model = get_base_model(self.queryset)
            if not base_model.objects.exists():     # exists省性能
                return self.queryset

            meta = base_model.objects.first()._meta
            field_names = [field.name for field in meta.fields]
            many_to_many_field_names = [field.name for field in meta.many_to_many]
            if many_to_many_field_names:
                field_names.extend(many_to_many_field_names)

            if self.queryset.exists():      # exists 比 count 省性能
                qs_i = self.queryset[0]
                if isinstance(qs_i, dict):
                    new_names = list(qs_i.keys())
                else:
                    new_dc: dict = qs_i.__dict__.copy()
                    new_dc.pop('_state')
                    new_names = list(new_dc.keys())

                # 可能用annotate增加了注释字段, 所以要处理一下, 避免过滤出错
                for new_name in new_names:
                    if new_name not in field_names:
                        field_names.append(new_name)

            field_names.append('pk')  # 将主键pk加进去作为过滤条件

            for fn, value in query_dc.items():
                filter_flag = False     # 是否过滤
                negative_flag = False   # 是否取否

                if fn:
                    # fn: str
                    if fn.startswith(self.negative_flag):
                        fn = fn[1:]
                        negative_flag = True

                    if f'__' in fn:
                        _fn = fn.split('__')[0]
                        if _fn in field_names or fn in field_names:
                            if FILTER_ALL_FIELDS or fn in self.filter_fields or _fn in self.filter_fields or fn == 'pk' or _fn == 'pk':
                                filter_flag = True
                    else:
                        if fn in field_names and (FILTER_ALL_FIELDS or fn in self.filter_fields or fn == 'pk'):
                            filter_flag = True

                if filter_flag:
                    if value is not None and value != '':  # 默认为空字符串时, 将不作为过滤条件
                        # print(fn, value)
                        convert_to_bool_flag = self.convert_to_bool_flag
                        if isinstance(value, str) and value.startswith(convert_to_bool_flag):
                            value = pure.convert_query_parameter_to_bool(value[len(convert_to_bool_flag):])

                        if isinstance(value, str) and fn.endswith('__isnull'):
                            value = pure.convert_query_parameter_to_bool(value)

                        dc = {fn: value}
                        if negative_flag:
                            self.queryset = self.queryset.exclude(**dc)
                        else:
                            self.queryset = self.queryset.filter(**dc)

        return self.queryset

    def _get_list_queryset(self):  # 兼容问题
        return self.get_list_queryset()

    def list(self, request, *args, **kwargs):
        query_dc = self.get_request_data()
        page_size = query_dc.get('page_size', self.pagination_class.page_size)

        GET_ALL = -999      # 获取全部
        p = query_dc.get('p', 1)

        try:
            p = int(p)

            if p == GET_ALL or int(page_size) == GET_ALL:
                p = 1
                page_size = 999999999

            my_api_assert_function(p > 0, f'页码p[{p}]必须为[正整数]!')
        except Exception as e:
            my_api_assert_function(0, f'页码[p: {p}] 必须为[正整数]!')

        context = self.get_serializer_context()

        serializer_class = self.get_serializer_class()
        resp, page_dc = paginate_qsls_to_dcls(self.queryset, serializer_class, page=p, per_page=page_size,
                                              context=context)
        ret = self.conv_data_format(resp, page_dc)
        return ret

    def conv_data_format(self, data, page_dc):
        # --- 是否展平为list, 而不是dc_ls
        flat_dc_ls = get_key_from_request_data_or_self_obj(self.get_request_data(), self, 'flat_dc_ls', get_type='bool')
        if flat_dc_ls and data and len(data[0]) == 1:
            data = [list(i.values())[0] for i in data]

        add_page_dc = get_key_from_request_data_or_self_obj(self.get_request_data(), self, 'add_page_dc', get_type='bool')
        if add_page_dc:
            ret = {
                'page_dc': page_dc,
                'data': data,
            }
        else:
            ret = data
        return ret

    def _conv_data_format(self, *args, **kwargs):
        return self.conv_data_format(*args, **kwargs)

    def get_key_from_query_dc_or_self(self, key, get_type=None):
        """
        优先检索query_dc是否有key, 其次检索self是否有key这个属性
        :param key: 变量名
        :return:
        """

        query_dc = self.get_request_data()
        ret_0 = getattr(self, key) if hasattr(self, key) else None

        if get_type == 'list':
            data = get_list(query_dc, key)
            # if data == ['']:
            #     data = []
        elif get_type == 'bool':
            value = query_dc.get(key)
            if value is not None:
                data = pure.convert_query_parameter_to_bool(value)
                if data is False:
                    return data
            else:
                return ret_0
        else:
            data = query_dc.get(key)

        # 让request携带的数据可以覆盖自身的key值
        ret_1 = data if data else None
        ret = ret_1 or ret_0
        return ret

    def _get_key_from_query_dc_or_self(self, *args, **kwargs):
        return self.get_key_from_query_dc_or_self(*args, **kwargs)


class BaseList(BaseListView):  # 向下兼容, 返回格式调整, 重写_conv_data_format.
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

    def get_post_type(self):
        post_type = self.request.data.get('post_type', 'create')
        self._post_type = post_type
        my_api_assert_function(not post_type or post_type in self.post_type_ls, f"操作类型post_type指定错误! 取值范围: {self.post_type_ls}")
        return post_type

    def post(self, request, *args, **kwargs):
        """增"""
        post_type = self.get_post_type()
        # post_type = request.data.get('post_type', 'create')
        # self._post_type = post_type
        # my_api_assert_function(not post_type or post_type in self.post_type_ls, f"操作类型post_type指定错误! 取值范围: {self.post_type_ls}")

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
        my_api_assert_function(qs_ls.exists(), '未找到id_ls对应的数据!')

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
        self.queryset = base_model.objects.filter(id__in=id_ls)
        # ret = self.get_serializer_class()(qs_ls, many=True).data
        ret, status, msg = self.get_list_ret(request, *args, **kwargs)
        return APIResponse(ret, status=status, msg=msg)

