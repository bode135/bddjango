"""
Basic building blocks for generic class based views.

We don't bind behaviour to http method handlers yet,
which allows mixin classes to be composed in interesting ways.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.settings import api_settings
from .utils import APIResponse, reset_db_sequence
from warnings import warn
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin, DestroyModelMixin
from .utils import my_api_assert_function
from .utils import get_statistic_fields_result


class MyCreateModelMixin(CreateModelMixin):
    """
    Create a model instance.
    """
    def create(self, request, *args, **kwargs):
        data = request.data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return APIResponse(serializer.data, status=201, msg='ok, 创建成功.')

    def perform_create(self, serializer):
        try:
            serializer.save()
        except Exception as e:
            warn('Warning: 序列化器保存错误! 可能是最近有csv/excel数据导入引起的主键冲突. \n详细信息:' + str(e))
            reset_db_sequence(self.queryset)
            serializer.save()


class MyUpdateModelMixin(UpdateModelMixin):
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return APIResponse(serializer.data, status=200, msg='ok, 更新成功.')


class MyDestroyModelMixin:
    """
    Destroy a model instance.
    """
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # try:
        #     instance = self.get_object()
        # except Exception as e:
        #     return APIResponse(None, status=403, msg='Error! error_msg:'+ str(e))
        self.perform_destroy(instance)
        return APIResponse(None, status=status.HTTP_204_NO_CONTENT, msg='ok, 删除成功.')

    def perform_destroy(self, instance):
        instance.delete()


class ListStatisticMixin:
    """
    增加统计分析结果statistic_dc, 写入ret中
    """
    statistic_fields = []               # 要统计的字段, 每个View都需要填写, 或者前端传参

    get_statistic_dc = True             # 是否获取
    statistic_size = 10000              # 返回的个数, 由于统计结果通常不多, 默认返回全部比较好
    statistic_descend = True            # 排序方式
    pop_name_ls = [None, ""]            # 要删除的key_name
    only_get_statistic_dc = False       # 是否仅返回statistic_dc, 不反data等其它信息

    statistic_actions = ['get_statistic_dc_func']  # 统计动作列表, 参考admin-actions设计, 但一般不用改动...有点多余...

    def get_list_ret(self, request, *args, **kwargs):
        ret, status, msg = super().get_list_ret(request, *args, **kwargs)

        for statistic_action in self.statistic_actions:
            if hasattr(self, statistic_action):
                get_statistic_dc_func = getattr(self, statistic_action)
                ret, status, msg = get_statistic_dc_func(ret, status, msg)
        return ret, status, msg

    def get_statistic_dc_func(self, ret, status, msg):
        my_api_assert_function(ret, '没有检索到数据~', 200)

        # 统计分析
        get_statistic_dc = self.get_key_from_query_dc_or_self('get_statistic_dc', get_type='bool')
        statistic_fields = self.get_key_from_query_dc_or_self('statistic_fields', get_type='list')
        only_get_statistic_dc = self.get_key_from_query_dc_or_self('only_get_statistic_dc', get_type='bool')
        if (get_statistic_dc or only_get_statistic_dc) and statistic_fields:
            statistic_size = self.get_key_from_query_dc_or_self('statistic_size')
            statistic_descend = self.get_key_from_query_dc_or_self('statistic_descend', get_type='bool')
            queryset = self.get_list_queryset()
            statistic_dc = get_statistic_fields_result(queryset, statistic_fields, statistic_size=statistic_size,
                                                       descend=statistic_descend)

            pop_name_ls = self.get_key_from_query_dc_or_self('pop_name_ls', get_type='list')
            if pop_name_ls:
                new_statistic_dc = {}
                for field, ls in statistic_dc.items():
                    new_ls = []
                    for dc in ls:
                        if dc.get('name') not in pop_name_ls:  # 没有'name'的情况一般是传入的元组
                            new_ls.append(dc)
                    new_statistic_dc.update({field: new_ls})
            else:
                new_statistic_dc = statistic_dc

            if only_get_statistic_dc:
                ret = new_statistic_dc
            else:
                add_page_dc = self.get_key_from_query_dc_or_self('add_page_dc', get_type='bool')
                my_api_assert_function(add_page_dc, 'add_page_dc的值必须为真!')
                ret.update({'statistic_dc': new_statistic_dc})
        return ret, status, msg



