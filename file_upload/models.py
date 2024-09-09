from django.db import models
from django.utils.functional import lazy
from bddjango.tools.base_orm_search import BaseOrmSearchModel


class FileSelection(models.Model):
    name = models.CharField(max_length=32, verbose_name="名称",  default=None, null=True, blank=True)
    path = models.CharField(max_length=128, verbose_name='路径', default=None, blank=True, null=True)

    class Meta:
        ordering = ('id',)
        verbose_name_plural = verbose_name = "上传路径选项"

    def __str__(self):
        return f'{self.id}__{self.name}'


def get_file_choices():
    """
    获取文件替换路径选择列表
    """
    try:
        qs_ls: models.QuerySet = FileSelection.objects.all()
        MAJORS = list(zip([getattr(qs, 'path') for qs in qs_ls], [getattr(qs, 'name') for qs in qs_ls]))
    except:
        MAJORS = [('_path', '_name')]
    return MAJORS


class UploadFile(BaseOrmSearchModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._meta.get_field('replace_path').choices = lazy(get_file_choices, list)()

    title = models.CharField(max_length=30, verbose_name="标题", default=None, null=True, blank=True)
    replace_path = models.CharField(max_length=256, choices=get_file_choices(), verbose_name="文件替换路径", db_collation=False, default=None, null=True, blank=True)
    file = models.FileField(verbose_name="文件", default=None, null=True, blank=True, upload_to='MyUploadFile')
    explain = models.TextField(verbose_name="说明", default=None, null=True, blank=True)

    upload_time = models.DateTimeField(verbose_name="添加时间", null=True, blank=True, auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="更新时间", null=True, blank=True, auto_now=True)
    # upload_time = models.DateField(verbose_name="添加时间", null=True, blank=True)
    # update_time = models.DateTimeField(verbose_name="更新时间", null=True, blank=True)

    class Meta:
        ordering = [models.F('update_time').desc(nulls_last=True), 'id']
        verbose_name_plural = verbose_name = "上传文件管理"

    # 综合检索设置
    search_field_conf = {
        'title': 1,
        'explain': 0.1,
    }
    search_debug = 1


