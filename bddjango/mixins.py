"""
Basic building blocks for generic class based views.

We don't bind behaviour to http method handlers yet,
which allows mixin classes to be composed in interesting ways.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.settings import api_settings
from .django import APIResponse, reset_db_sequence
from warnings import warn
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin, DestroyModelMixin


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

