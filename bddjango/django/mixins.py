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
from .utils import get_md5_query_for_qs_ls
from django.core.cache import cache


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

    - 取值示例:
        statistic_fields = [('fen_lei_hao', 'fen_lei_ming'), 'shi_jian']
        order_config_dc_ls = [
            {
                'name': 'shi_jian',
                'ordering': '-shi_jian',
                # 'pop_name_ls': ['1999'],  # 删除一些值
                # 'loc_ls': ['2005', '2001', '2020']  # 特定顺序返回
            }
        ]
    """
    cache_expired_time__statistic_dc = 0       # 统计结果的缓存时间

    statistic_fields = []               # 要统计的字段, 每个View都需要填写, 或者前端传参

    get_statistic_dc = True             # 是否获取
    statistic_size = 10000              # 返回的个数, 由于统计结果通常不多, 默认返回全部比较好
    statistic_descend = 1            # 排序方式
    pop_name_ls = [None, ""]            # 要删除的key_name
    only_get_statistic_dc = False       # 是否仅返回statistic_dc, 不反data等其它信息

    order_config_dc_ls = None           # 指定需要特制排序`ordering`或`pop_name_ls`的字段

    statistic_actions = ['get_statistic_dc_func']  # 统计动作列表, 参考admin-actions设计, 但一般不用改动...有点多余...

    def get_list_ret(self, request, *args, **kwargs):
        ret, status, msg = super().get_list_ret(request, *args, **kwargs)

        for statistic_action in self.statistic_actions:
            if hasattr(self, statistic_action):
                get_statistic_dc_func = getattr(self, statistic_action)
                ret, status, msg = get_statistic_dc_func(ret, status, msg)
        return ret, status, msg

    def get_statistic_dc_func(self, ret, status, msg):
        # my_api_assert_function(ret, 'ListStatisticMixin没有检索到数据~', 200)
        get_page_dc = self.get_key_from_query_dc_or_self('get_page_dc', get_type='bool')
        if not get_page_dc:
            return ret, status, msg

        # 统计分析
        get_statistic_dc = self.get_key_from_query_dc_or_self('get_statistic_dc', get_type='bool')
        statistic_fields = self.get_key_from_query_dc_or_self('statistic_fields', get_type='list')
        only_get_statistic_dc = self.get_key_from_query_dc_or_self('only_get_statistic_dc', get_type='bool')
        if (get_statistic_dc or only_get_statistic_dc) and statistic_fields:
            statistic_size = self.get_key_from_query_dc_or_self('statistic_size')
            # statistic_descend = self.get_key_from_query_dc_or_self('statistic_descend', get_type='bool')
            statistic_descend = self.get_key_from_query_dc_or_self('statistic_descend')
            order_config_dc_ls = self.order_config_dc_ls

            # region # --- 这里使用缓存保存`statistic_dc`结果
            qs_ls = self.get_list_queryset()

            expired_time = self.cache_expired_time__statistic_dc

            query = get_md5_query_for_qs_ls(qs_ls, header="statistic_dc__")

            statistic_dc = None
            if expired_time:
                statistic_dc = cache.get(query)

            if statistic_dc is None:
                statistic_dc = get_statistic_fields_result(qs_ls, statistic_fields, statistic_size=statistic_size,
                                                           descend=statistic_descend,
                                                           order_config_dc_ls=order_config_dc_ls)
            if expired_time:
                cache.set(query, statistic_dc, expired_time)
            # endregion

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
                get_page_dc = self.get_key_from_query_dc_or_self('get_page_dc', get_type='bool')
                # my_api_assert_function(get_page_dc, '`get_page_dc`的值必须为真!')
                if get_page_dc:
                    ret.update({'statistic_dc': new_statistic_dc})
        return ret, status, msg


class DownloadFileMixin:
    """
    下载文件(若目标为文件夹, 则打包为zip下载)
    """

    default_path = None
    path_field_name = None

    @staticmethod
    def _file_iterator(file_name, open_model='rb', chunk_size=512):
        with open(file_name, open_model) as f:  # , encoding=encoding
            while True:
                c = f.read(chunk_size)
                if c:
                    yield c
                else:
                    break

    @staticmethod
    def download_by_file_path(download_file_path):
        # --- 返回文件流
        from django.http import StreamingHttpResponse
        from django.utils.http import urlquote
        import os

        download_file_name = os.path.basename(download_file_path)
        response = StreamingHttpResponse(DownloadFileMixin._file_iterator(download_file_path))
        # response['Content-Type'] = 'application/octet-stream'
        filename = urlquote(download_file_name)
        response['Content-Type'] = 'application/x-zip-compressed'
        response['Content-Disposition'] = 'attachment;filename="{0}"'.format(filename)
        return response

    def download_file(self, request, queryset=None, model=None):
        import os

        assert queryset.count() == 1, '一次只允许下载一个文件!'
        obj = queryset[0]

        src = getattr(obj, self.path_field_name) if self.path_field_name else self.default_path
        assert src, '目标路径不能为空! 请指定`path_field_name`或者`default_path`!'
        assert os.path.exists(src), f'目标路径[{src}]不存在!'

        if os.path.isdir(src):
            # --- 创建临时路径
            from bddjango import get_base_model

            md = get_base_model(obj)
            tmp_file_dir_path = f"tempdir/{md._meta.app_label}/{md._meta.object_name}"
            os.makedirs(tmp_file_dir_path, exist_ok=True)

            # --- 打包为zip
            from bddjango.tools.zipDir import zipDir

            zip_file_name = f'{obj}.zip'
            dst = os.path.join(tmp_file_dir_path, zip_file_name)

            zipDir(src, dst)

            download_file_path = dst

            # --- 清理临时文件
            from bddjango.tools.remove_temp_file import remove_temp_file
            remove_temp_file(tmp_file_dir_path)
        else:
            download_file_path = src

        response = DownloadFileMixin.download_by_file_path(download_file_path)
        return response

    download_file.short_description = '下载文件'
    # download_file.type = 'warning'
    download_file.icon = 'el-icon-download'
    download_file.enable = True
    download_file.confirm = f"确定{download_file.short_description}?"


