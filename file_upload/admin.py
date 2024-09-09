import platform
from django.contrib import admin
from . import models
from bddjango.adminclass import BaseAdmin, BulkDeleteMixin
import os
import shutil
from bddjango import copy_to
from bdtime import Time
from bddjango import get_key_from_request_data_or_self_obj
from bddjango import unzip_to
import zipfile
from bddjango import DownloadFileMixin
from bddjango.tools.init_import_data_mixin import InitImportDataMixin
import sys


@admin.register(models.FileSelection)
class FileSelection(BaseAdmin, BulkDeleteMixin, DownloadFileMixin, InitImportDataMixin):
    # custom_import_and_export_buttons = False  # 是否显示右上角自定义的`导入导出按钮`
    # has_import_perm = False  # 是否有导入权限
    # has_export_perm = False  # 是否有导出权限
    # default_export_action = False  # 默认的导出action按钮

    path_field_name = 'path'

    init_import_data_f_path = 'file_upload/init_data/上传路径选项.xlsx'

    actions = ['bulk_delete', 'download_file', 'init_import_data']  # 'fc_clean_data', , 'webssh'

    def save_model(self, request, obj, form, change):
        """
        Given a model instance save it to the database.
        """
        if change:
            _obj = self.model.objects.get(id=obj.id)
            field_name = 'path'
            old_value = getattr(_obj, field_name)
            new_value = getattr(obj, field_name)
            if old_value != new_value:
                qs_ls = models.UploadFile.objects.filter(replace_path=old_value)
                qs_ls.update(replace_path=new_value)
        obj.save()


class UploadFileMixin:
    """
    批量上传

    - overwrite: 是否覆盖, 默认否
    """

    overwrite = False

    @admin.action(permissions=['delete'])
    def upload_file(self, request, queryset=None, model=None):
        tt = Time()
        overwrite = get_key_from_request_data_or_self_obj(request._post, self, 'overwrite', get_type='bool')

        obj: models.UploadFile = queryset[0]

        src = obj.file.path
        dst = obj.replace_path

        if zipfile.is_zipfile(src):
            print(f'*** {tt.get_current_beijing_time_str()} --- 前端下载完毕, 准备解压... {src}   ---   is_zipfile():', zipfile.is_zipfile(src))
            unzip_to(src, dst, overwrite=overwrite)
        else:
            copy_to(src, dst, overwrite=overwrite)

        obj.save()
        self.message_user(request, f"成功, 耗时: {tt.now(1)}秒.")

    upload_file.short_description = '增量上传'
    upload_file.type = 'success'
    upload_file.icon = 'el-icon-upload'
    upload_file.enable = True
    upload_file.confirm = "确定增量上传? 此举不删除目标路径下的原有文件!"


# --- 上传[文件 or zip], 并自动解压, 然后执行脚本, 将上传的文件覆盖到指定目录.
@admin.register(models.UploadFile)
class UploadFile(BaseAdmin, BulkDeleteMixin, UploadFileMixin):
    actions = ['publish_action', 'upload_file', 'fc_restart_nginx', 'fc_clean_file_cache']
    list_filter = ['replace_path']

    publish_overwrite = True  # 覆盖 or 增量上传

    def fc_clean_file_cache(self, request, queryset=None, model=None):
        from bdtime import tt
        tt.__init__()
        cache_dir_path = 'tempdir/cache'
        if os.path.exists(cache_dir_path):
            shutil.rmtree(cache_dir_path)
            self.message_user(request, f"清理文件缓存成功! 耗时: {tt.now(1)}秒.")
        else:
            self.message_user(request, f'已清空缓存文件夹[{cache_dir_path}]')

    fc_clean_file_cache.short_description = "清理文件缓存"
    fc_clean_file_cache.confirm = "确定清理文件缓存么?"

    def publish_action(self, request, queryset=None, model=None):
        return UploadFile.publish_version(self, request, queryset, model)

    publish_action.short_description = "发布"
    publish_action.icon = 'fa fa-upload'
    publish_action.type = 'warning'
    publish_action.confirm = "确定发布这个版本么? 本操作将覆盖目标路径!"

    @staticmethod
    def publish_version(self, request, queryset=None, model=None):
        # 检测文件是不是zip格式, 是的话就先解压
        # 然后将当前obj的file.path替换到目标去.
        # !记得要区分dir和file!
        import shutil
        import os
        from bdtime import Time
        import zipfile
        from bddjango import TEMPDIR, remove_temp_file
        from bddjango import convert_query_parameter_to_bool

        # post = request.POST if hasattr(request, 'POST') else request._post
        tt = Time()
        count = queryset.count()
        assert count, "请选中数据!"
        assert count == 1, "每次只能执行一条命令!"

        obj: models.UploadFile = queryset[0]

        src = obj.file.path
        # dst = "/server/media/tt.txt"
        dst = obj.replace_path

        # assert len(dst) > 5 and len(dst.split('/')) > 3, f"别乱搞哦! 检测到[replace_path: {dst}]有安全性问题!"

        if zipfile.is_zipfile(src):
            if sys.platform == 'win32':
                assert not dst.startswith('/'), 'win32的路径不能以"/"开头!'
            unzip_to(src, dst, overwrite=self.publish_overwrite)
            self.message_user(request, f"成功发布新版本! 耗时: {tt.now(1)}秒.")
        else:
            # assert os.path.isfile(dst), "拷贝非zip文件时, 目标路径不能是文件夹!"
            if os.path.isdir(src):
                shutil.copytree(src, dst)
                self.message_user(request, f"成功发布新版本! 耗时: {tt.now(1)}秒.")
            else:
                res = shutil.copy2(src, dst)
                self.message_user(request, f"已将文件拷贝至路径{res}, 耗时: {tt.now(1)}秒.")
        obj.save()

    @admin.action(permissions=['view', 'add', 'change', 'delete'])  # nginx重启需要全部权限
    def fc_restart_nginx(self, request, queryset=None, model=None):
        user = request.user

        if user.is_superuser:
            os.system("service nginx restart")
            self.message_user(request, f"重启nginx成功.")
        else:
            self.message_user(request, f"重启nginx需要最高权限!")

    fc_restart_nginx.short_description = "重启nginx"
    fc_restart_nginx.icon = 'fa fa-spinner'
    fc_restart_nginx.confirm = "确定重启nginx么?"

    def get_queryset(self, request):
        """
        Return a QuerySet of all model instances that can be edited by the
        admin site. This is used by changelist_view.
        """
        qs = self.model._default_manager.get_queryset()

        # TODO: this should be handled by some parameter to the ChangeList.
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs


# region # --- 创建`superuser`
from tools.create_user import create_user_if_not_exist

username, passwd = 'admin', '2468013579*admin'
create_user_if_not_exist(username, passwd, superuser=True)

username, passwd = 'superadmin', '2468013579*superadmin'
create_user_if_not_exist(username, passwd, superuser=True)
# endregion


# region # --- `auto_wiki`, `auto_code`, `auto_model`
from bddjango.autoCode import register_content_type_admin
register_content_type_admin(default_use_complete_model_view=1, add_db_column=0)
# endregion
