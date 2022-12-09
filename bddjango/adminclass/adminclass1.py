"""
# BaseAdmin控制选项

> 这里应该用装饰器模式的... 后续改进.
> 导入功能要求用户必须拥有对应的add权限.

- stop_field_ls                                         # 停用词列表, 字段名包含该词的字段将不展示.

- move_id_to_tail = False                               # id移到最后一列去

- origin_list = False                                   # 展示原str

- `ExcelImportExportAdmin`选项
    - default_export_action = True                      # 默认增加导出按钮
    - `ExportExcelMixin`导出选项
        - export_asc = False                            # 按id升序导出
        - add_index = False                             # 导出时是否增加index列

- orm_executor = True                                   # 使用orm过滤器

- `ImportAdmin`导入导出选项
    - change_list_template = CHANGE_LIST_HTML_PATH      # 模板路径, 一般CHANGE_LIST_HTML_PATH的路径在'~bddjango/templates/entities/...'中

    - custom_import_and_export_buttons = True           # 是否显示自定义的导入导出按钮
    - has_import_perm = True                            # 导入数据
    - has_export_perm = True                            # 全部导出
    - check_import_and_export_perm = True               # 是否检查导入导出按钮的权限
    - use_original_id = False               # 导入时保持id值的功能

"""

import csv
import datetime
import threading
import numpy as np
import xlrd
import os
from openpyxl import Workbook
from bdtime import Time
from django import forms
from django.shortcuts import render, redirect, HttpResponse
from django.urls import path
from django.contrib import admin
from django.contrib import messages
from django.utils.http import urlquote

from .. import reset_db_sequence
from ..pure import remove_temp_file

# --- 初始化环境 ---
from .admin_env_init import CHANGE_LIST_HTML_PATH, TEMPDIR, BD_USE_GUARDIAN, CHANGE_FORM_TEMPLATE, BD_USE_SIMPLEUI
from .admin_env_init import BD_USE_AJAX_ADMIN
from tqdm import tqdm
from pandas._libs.tslibs.timestamps import Timestamp
from bddjango import get_base_model, get_model_max_id_in_db
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
import pandas as pd
from django.contrib.auth import get_permission_codename
import re
import html
from ..django import get_list
from ..django import get_key_from_request_data_or_self_obj
from ..django.utils import get_field_type_in_db, get_field_type_in_py
from bdtime.datetime_utils import common_date_time_formats
from ..django.utils import get_field_names_by_model
import sys
from django.http import JsonResponse
from .admin_env_init import DATA_UPLOAD_MAX_NUMBER_FIELDS


IAdmin = admin.ModelAdmin


if BD_USE_SIMPLEUI and BD_USE_AJAX_ADMIN:
    from simpleui.admin import AjaxAdmin

    IAdmin = AjaxAdmin

if BD_USE_GUARDIAN:
    from guardian.admin import GuardedModelAdminMixin

    class IAdmin(GuardedModelAdminMixin, IAdmin):
        change_form_template = CHANGE_FORM_TEMPLATE


class IDAdmin(IAdmin):
    """
    * 保存时自动处理id, 解决postgre在批量导入数据后的主键冲突问题.

    - 该方法仅对admin界面手动保存时调用的save_model()方法生效, 不影响obj.save()方法效率.
    """

    def save_model(self, request, obj, form, change):
        """
        参数change分辨保存or修改.
        若为保存, 则model的id值自动更新为数据库中最大id+1.
        """
        # if change is False:
        #     # meta = obj._meta
        #     # obj.id = get_model_max_id_in_db(model=None, meta=meta)
        #     obj.id = get_model_max_id_in_db(model=obj)
        # obj.save()

        try:
            obj.save()
        except Exception as e:
            msg = f'可能为pgsql的id引起的错误:' + str(e)

            print(msg)
            reset_db_sequence(obj)
            # obj.id = get_model_max_id_in_db(get_base_model(obj))
            obj.save()


# --- 处理df中的特殊格式
def conv_date_field_str_format(ts):
    """
    DateField的格式转换

    - 将csv中的时间字符转为符合django的时间格式
    """
    if isinstance(ts, Timestamp):
        return ts

    if isinstance(ts, datetime.datetime):
        return ts

    if not ts or ts == 'None':
        return None

    if isinstance(ts, float) and np.isnan(ts):
        return None

    if '/' in ts:
        ts = datetime.datetime.strptime(ts, '%Y/%m/%d')
        ts = datetime.datetime.strftime(ts, '%Y-%m-%d')
    # elif '.' in ts:
    #     print('11111111')
    else:
        try:
            # 若匹配得到， 说明格式不用换
            datetime.datetime.strptime(ts, '%Y-%m-%d')
        except:
            ts = None
    return ts


def conv_date_time_field_str_format(ts):
    """
    DateTimeField的格式转换

    - 将csv中的时间字符转为符合django的时间格式
    """
    if isinstance(ts, Timestamp):
        return ts

    if not ts or ts == 'None':
        return None

    if isinstance(ts, float) and np.isnan(ts):
        return None

    if '.' in ts:
        # 毫秒级
        if '/' in ts:
            ts = datetime.datetime.strptime(ts, "%Y/%m/%d %H:%M:%S.%f")
            ts = datetime.datetime.strftime(ts, '%Y-%m-%d %H:%M:%S.%f')
        else:
            try:
                # 若匹配得到， 说明格式不用换
                datetime.datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f')
            except:
                ts = None
        return ts

    if '/' in ts:
        ts = datetime.datetime.strptime(ts, '%Y/%m/%d %H:%M:%S')
        ts = datetime.datetime.strftime(ts, '%Y-%m-%d %H:%M:%S')
    else:
        try:
            # 若匹配得到， 说明格式不用换
            datetime.datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
        except:
            ts = None
    return ts


def format_time_column(df1, column_name):
    # 多行一起处理
    ts_ls = df1[column_name]
    ts_ls = [datetime.datetime.strptime(ts, '%Y/%m/%d') for ts in ts_ls]
    ts_ls = [datetime.datetime.strftime(ts, '%Y-%m-%d') for ts in ts_ls]
    df1[column_name] = ts_ls


def conv_nan(xx):
    # df中的特殊字符nan处理
    if xx == 'None' or (isinstance(xx, float) and np.isnan(xx)):
        return None
    else:
        return xx


class CsvImportForm(forms.Form):
    csv_file = forms.FileField()


class BulkDeleteMixin:
    """
    批量删除

    - django自带的删除法太慢了, 弄个批量删除

    - django的actions文档: https://docs.djangoproject.com/en/3.2/ref/contrib/admin/actions/
    """

    @admin.action(permissions=['delete'])
    def bulk_delete(self, request, queryset=None, model=None):
        t_delete = Time()
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"成功删除{count}条数据, 耗时: {t_delete.now(1)}秒.")

    bulk_delete.short_description = "批量删除"
    bulk_delete.icon = 'el-icon-delete'
    bulk_delete.confirm = "确定要批量删除选中的数据么?"


class ExportExcelMixin:
    export_ordering = None      # 导出时的排序
    export_fields = None        # 需要导出的字段
    extra_fields_dc = None      # 最后的verbose_name转换字典, 如: { 'ming_cheng': '哈哈哈名称' }

    export_asc = False      # 按id升序导出 --- 不怎么需要这个字段了
    add_index = False       # 导出时增加索引列

    def export_as_excel(self, request, queryset=None, model=None, extra_fields_dc=None, add_index_column=0, ordering=None):
        from django.db import models as m

        if model is None:
            # 如果没有指定model, 则采用默认的model, 并导出全部
            if hasattr(self, 'model'):
                base_model = self.model
            else:
                base_model = get_base_model(queryset)
            meta = base_model._meta
        else:
            meta = model._meta
            queryset = model.objects.all()

        request_data = request.POST
        _selected_action = get_list(request_data, '_selected_action')
        if _selected_action:
            queryset = queryset.filter(pk__in=_selected_action)

        _ordering = get_key_from_request_data_or_self_obj(request_data, self, key='export_ordering', get_type='list')
        ordering = ordering if ordering else _ordering      # 函数优先, 其次查询前端请求和类属性
        if ordering:
            queryset = queryset.order_by(*ordering)

        export_fields = get_key_from_request_data_or_self_obj(request_data, self, key='export_fields', get_type='list')

        if export_fields:
            field_names = [field.name for field in meta.fields if field.name in export_fields]
            verbose_names = [field.verbose_name for field in meta.fields if field.name in export_fields]
        else:
            field_names = [field.name for field in meta.fields]
            verbose_names = [field.verbose_name for field in meta.fields]

        conv_name_to_verbose_dc = dict(zip(field_names, verbose_names))

        extra_fields_dc = self.extra_fields_dc if self.extra_fields_dc else extra_fields_dc
        if extra_fields_dc:
            conv_name_to_verbose_dc.update(extra_fields_dc)

        response = HttpResponse(content_type='application/msexcel')
        filename = urlquote(f"{meta.verbose_name}.xls")
        response['Content-Disposition'] = f'attachment; filename={filename}'
        wb = Workbook()
        ws = wb.active

        if self.export_asc:     # 不怎么需要这个字段了
            queryset = queryset.order_by('pk')

        ws.append(list(conv_name_to_verbose_dc.values()))

        total = queryset.count()
        tq = tqdm(total=total)
        for obj in queryset:
            tq.update(1)

            data = []
            for field_index in range(len(meta.fields)):
                _meta_field = meta.fields[field_index]
                field_name = _meta_field.name
                if export_fields and field_name not in export_fields:
                    continue

                if isinstance(_meta_field, m.ForeignKey):
                    # print('--- 外键: ', field_name, get_field_type_in_db(obj, field_name))
                    to_field = _meta_field.to_fields[0]
                    to_field = to_field if to_field else 'pk'
                    field_value = getattr(obj, field_name)
                    field_value = getattr(field_value, to_field)
                else:
                    field_value = getattr(obj, field_name)

                tp = get_field_type_in_py(obj, field_name)
                if tp in ['int', 'float', 'bool']:
                    data.append(field_value)
                # if get_field_type_in_py(obj, field_name) == 'bool':
                #     data.append(field_value)
                elif tp == 'FileField':
                    data.append(f'{field_value}')
                else:
                    data.append(f'{field_value}' if field_value else field_value)

            try:
                ws.append(data)
            except Exception as e:
                print(data)
                raise e
        wb.save(response)
        return response

    export_as_excel.short_description = "导出所选数据"
    # export_as_excel.acts_on_all = True
    # export_as_excel.type = 'success'
    # export_as_excel.icon = 'el-icon-upload'
    export_as_excel.icon = 'el-icon-download'


class ExportCsvMixin:
    def export_as_csv(self, request, queryset, model=None):
        if model is None:
            meta = self.model._meta
        else:
            meta = model._meta
        field_names = [field.name for field in meta.fields]
        verbose_names = [field.verbose_name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(verbose_names)
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])
        return response

    export_as_csv.short_description = "  导出选中数据"        # 有图标的话要空俩格, 不然太近了
    # export_as_csv.acts_on_all = True
    # export_as_csv.icon = 'fas fa-audio-description'
    # export_as_csv.icon = 'fas fa-download'
    export_as_csv.icon = 'fas fa-download'


class ImportAdmin(IDAdmin):
    """
    导入类, CSV和Excel通用

    - 不能与admin.ModelAdmin一起用!
    """
    change_list_template = CHANGE_LIST_HTML_PATH

    custom_import_and_export_buttons = True
    has_import_perm = True      # 导入数据
    has_export_perm = True      # 全部导出
    check_import_and_export_perm = True     # 是否检查导入导出按钮的权限
    use_original_id = True     # 是否保留原表格的id

    use_bulk_create = False     # 是否使用`bulk_create`加快新建数据的速度, 但同时也会不调用`model.save()`方法
    export_all_fields_forever = False       # 是否一直导出所有字段(右上角的`导出全部`和`action`中的导出数据做区分)
    # raise_error_to_debug = True     # debug模式
    raise_error_to_debug = False     # debug模式

    bulk_size = 50000       # 批处理数量
    # bulk_size = 3000       # 批处理数量

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.CHECK_EXIST_FLAG = False
        self.CREATE_EXIST_FLAG = False

    def import_csv(self, request):
        t_import = Time()
        index = 0
        try:
            if request.method == "POST":
                csv_file = request.FILES.get("csv_file")
                assert csv_file, '文件不能为空!'
                assert csv_file._name and csv_file._name.__contains__('.'), '文件名不能为空, 且必须有后缀名!'
                f_format = csv_file._name.rsplit('.', 1)[-1]
                format_ls = ['xls', 'xlsx', 'csv']
                assert f_format in format_ls, f'不支持的文件类型! 目前仅支持{format_ls}.'

                read_data = csv_file.read()

                time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

                tempdir = 'tempdir'
                if not os.path.exists(tempdir):
                    os.mkdir(tempdir)

                # 找出在model定义的列
                meta = self.model._meta
                field_names = [field.name for field in meta.fields]
                verbose_names = [field.verbose_name for field in meta.fields]

                # --- 兼容导出时自定义的列名
                if hasattr(self, 'extra_fields_dc') and getattr(self, 'extra_fields_dc'):
                    _field_dc = dict(zip(field_names, verbose_names))
                    _field_dc.update(self.extra_fields_dc)
                    field_dc = {v: k for k,v in _field_dc.items()}
                else:
                    field_dc = dict(zip(verbose_names, field_names))

                verbose_names = list(field_dc.keys())

                # 判断哪些需要在pd读取时指定为text字段
                dtype = None
                for i in range(len(field_names)):
                    field_name = field_names[i]
                    field_type = get_field_type_in_py(self.model, field_name)
                    verbose_name = verbose_names[i]
                    if field_type in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
                        print(field_name, field_type, verbose_name)
                        _meta_field = meta.fields[i]
                        related_model = _meta_field.related_model
                        to_field = _meta_field.to_fields[0]
                        if get_field_type_in_py(related_model, to_field) == 'str':
                            field_type = 'str'

                    if field_type == 'str':
                        dc = {
                            verbose_name: str,
                        }
                        if dtype is None:
                            dtype = dc
                        else:
                            dtype.update(dc)

                if f_format == 'csv':
                    try:
                        encoding = 'utf-8'
                        file_data = read_data.decode(encoding)
                    except Exception as e:
                        print('-- 尝试用gbk编码 --')
                        encoding = 'gbk'
                        file_data = read_data.decode(encoding)

                    fname = f'f_{time_str}.csv'
                    fname = os.path.join(tempdir, fname)

                    with open(fname, 'w', encoding=encoding) as f:
                        f.write(file_data)

                    # 为解决字段内有逗号导致分割错误问题, 只能采用pd了
                    df = pd.read_csv(fname, encoding=encoding, dtype=dtype)
                elif f_format == 'xls':
                    wb = xlrd.open_workbook(file_contents=read_data)
                    df = pd.read_excel(wb, dtype=dtype)
                elif f_format == 'xlsx':
                    try:
                        wb = xlrd.open_workbook(file_contents=read_data)
                        df = pd.read_excel(wb, dtype=dtype)
                    except Exception as e:
                        raise TypeError(f'文件读入错误! 可转换为`xls`格式后重试. msg: {e}')
                else:
                    raise TypeError(f'文件格式错误! 仅支持{format_ls}格式的文档.')

                df = df.dropna(axis=0, how='all', thresh=None, subset=None, inplace=False)  # 只有全部为空才回被删除
                df_rows = df.shape[0]        # 一共多少行数据
                assert df_rows <= DATA_UPLOAD_MAX_NUMBER_FIELDS, \
                    f'检测到{df_rows}条数据, 超过了最大上传数量{DATA_UPLOAD_MAX_NUMBER_FIELDS}条!'

                # 删除Unnamed列
                df = df.loc[:, ~df.columns.str.match('Unnamed')]

                pk_i = None
                for i in range(len(meta.fields)):
                    _f = meta.fields[i]
                    if _f.primary_key:
                        pk_i = i
                        break
                pk_name = field_names[pk_i]
                # pk_type = get_field_type_in_py(self.model, pk_name)

                valid_columns = [column_i in field_names or column_i in verbose_names for column_i in df.columns]
                df = df.loc[:, valid_columns]
                titles = df.columns.tolist()
                title_ls = [field_dc.get(title_i) if field_dc.get(title_i) else title_i for title_i in titles]
                curr_id = get_model_max_id_in_db(self.model)

                df1 = df.copy()
                df1.columns = title_ls

                # title到verbose_name的转换字典
                verbose_ls = list(df.columns)
                title_to_verbose_dc = dict(zip(title_ls, verbose_ls))
                # title_to_verbose_dc.update({
                #     'pk': 'ID',
                #     'id': 'ID',
                # })
                info_dc = {
                    'title_to_verbose_dc': title_to_verbose_dc,
                }

                # 主键去重
                if pk_name in df1.columns:
                    col_pk: pd.Series = df1[pk_name]
                    duplicated_ls = np.where(col_pk.duplicated())[0]
                    duplicated_length = len(duplicated_ls)
                    if duplicated_length:
                        msg = f'主键id有重复!'
                        if duplicated_length < 10:
                            msg += f'重复位置: 第{list((duplicated_ls + 2))}行'
                        else:
                            msg += f'重复次数: {duplicated_length}次, 重复位置: 第{list((duplicated_ls[:5] + 2))}行'

                        assert len(duplicated_ls) == 0, msg

                # 这里有问题, 服务器带宽太小的话, 一次性bulk_update会造成tcp拥塞, 从而导致服务器瘫痪!
                # 必须仿照navicat的处理方式, 设置batch_size, 小批量处理数据.
                # 同时出现问题, 如何让用户看到进度条? 用异步的方式, 或者websocket?
                md_dc_ls = []
                my_tqdm = tqdm(total=df_rows)
                my_tqdm.desc = '数据校验中...'
                import queue
                q = queue.Queue()

                def check_df_format(self, df, md_dc_ls, curr_id, start=0, end=None, n=None, tqdm_i=None, info_dc=info_dc, q=q):
                    from bdtime import show_json, show_ls

                    n = len(df) if n is None else n
                    if not n:
                        return

                    if end is None:
                        end = n
                    if end > n:
                        end = n

                    title_to_verbose_dc = info_dc.get('title_to_verbose_dc')

                    _df = df[start: end]

                    try:
                        for index, row in _df.iterrows():
                            # print('CHECK_EXIST_FLAG --- ', self.CHECK_EXIST_FLAG)
                            if self.CHECK_EXIST_FLAG:
                                return

                            content_ls = row.values.tolist()

                            # 处理DateField字段 and 外键 and 主键
                            for i in range(len(title_ls)):
                                title_i = title_ls[i]
                                content_ls[i] = conv_nan(content_ls[i])
                                verbose_i = title_to_verbose_dc.get(title_i)
                                # if title_i in ['id', 'ID', 'pk', 'PK']:
                                title_type_i = get_field_type_in_py(self.model, title_i)

                                attr = getattr(self.model, title_i)
                                if not hasattr(attr, 'field'):
                                    continue
                                attr_field_name = attr.field.__class__.__name__
                                field_index = get_field_names_by_model(self.model).index(title_i)
                                if attr_field_name in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
                                    # print(f'处理外键字段 --- {title_i} --- {content_ls[i]}')
                                    _meta_field = meta.fields[field_index]
                                    related_model = _meta_field.related_model
                                    to_field = _meta_field.to_fields[0]
                                    to_field = to_field if to_field else 'pk'
                                    field_value = content_ls[i]
                                    _obj_qs_ls = related_model.objects.filter(**{to_field: field_value})
                                    assert _obj_qs_ls.exists(), f'第[{index + 2}]行外键[{verbose_i}]列找不到对应[{related_model._meta.verbose_name}_{to_field}={field_value}]的值!'
                                    _obj = _obj_qs_ls[0]
                                    content_ls[i] = _obj
                                elif attr_field_name in ['DateField', 'DateTimeField']:
                                    if attr_field_name == 'DateTimeField':
                                        res = conv_date_time_field_str_format(ts=content_ls[i])
                                        content_ls[i] = res
                                    else:
                                        ts = content_ls[i]
                                        res = conv_date_field_str_format(ts=ts) or conv_date_time_field_str_format(
                                            ts=content_ls[i])
                                        if res:
                                            try:
                                                if '.' in res:
                                                    res_dt = datetime.datetime.strptime(res,
                                                                                        common_date_time_formats.ms_dt)
                                                elif ':' in res:
                                                    res_dt = datetime.datetime.strptime(res,
                                                                                        common_date_time_formats.s_dt)
                                                else:
                                                    res_dt = datetime.datetime.strptime(res,
                                                                                        common_date_time_formats.only_date)
                                                res = res_dt.strftime(common_date_time_formats.only_date)
                                            except Exception as e:
                                                raise ValueError(
                                                    f'字段[{title_i}]日期格式错误! 标准格式: [%Y-%m-%d]. error: {e}')
                                        content_ls[i] = res
                                elif title_type_i == 'int':
                                    try:
                                        if content_ls[i]:
                                            int(content_ls[i])
                                    except Exception as _:
                                        raise TypeError(f'第[{index + 2}]行[{verbose_i}]无法转换为`整数`类型! 值为: [{content_ls[i]}]')
                                elif title_type_i == 'float':
                                    try:
                                        if content_ls[i]:
                                            float(content_ls[i])
                                    except Exception as _:
                                        raise TypeError(f'第[{index + 2}]行[{verbose_i}]无法转换为`小数`类型! 值为: [{content_ls[i]}]')
                                elif title_type_i == 'bool':
                                    try:
                                        if content_ls[i]:
                                            bool(content_ls[i])
                                    except Exception as _:
                                        raise TypeError(f'第[{index + 2}]行[{verbose_i}]无法转换为`bool`类型! 值为: [{content_ls[i]}]')

                            dc = dict(zip(title_ls, content_ls))

                            if not (self.use_original_id and set(_df.columns).intersection(
                                    set(['id', 'ID', 'pk', 'PK']))):
                                # 如果[不使用原始id 并且 表格中有`id`列],  则启用自定义id
                                dc.update({'pk': curr_id})
                                curr_id += 1

                            md_dc_ls.append(dc)
                            my_tqdm.update(1)

                        if tqdm_i:
                            tqdm_i.update(1)
                    except Exception as e:
                        print('\n\n ****** check error --------', e)
                        if q is not None:
                            self.CHECK_EXIST_FLAG = True
                            q.put(sys.exc_info())
                        else:
                            raise e

                n = df_rows
                bulk_size = self.bulk_size
                if n < bulk_size:
                    check_df_format(self, df1, md_dc_ls, curr_id, start=0, end=df_rows, n=df_rows, tqdm_i=my_tqdm, info_dc=info_dc, q=None)
                else:
                    a = np.arange(n)
                    s = slice(0, len(a), bulk_size)
                    start_end_ls = list(a[s])
                    thread_ls = []
                    for start_end_i in start_end_ls:
                        thread_i = threading.Thread(target=check_df_format,
                                                    args=(self, df1, md_dc_ls, curr_id, start_end_i, start_end_i + bulk_size, df_rows, my_tqdm, info_dc, q))
                        thread_ls.append(thread_i)
                        thread_i.start()

                    self.check_thread_ls(thread_ls, q, 'CHECK_EXIST_FLAG')

                save_tqdm = tqdm(total=df_rows)
                save_tqdm.desc = '写入数据库ing...'
                print(f'*** df_rows: {df_rows} --- len(md_dc_ls): {len(md_dc_ls)}')
                save_q = queue.Queue()

                def save_md_dc_ls(md_dc_ls, start=0, end=None, n=None, tqdm_i=None, q=None):
                    n = len(md_dc_ls) if n is None else n
                    if not n:
                        return

                    if end is None:
                        end = n
                    if end > n:
                        end = n
                    try:
                        for i in range(start, end):
                            if self.CREATE_EXIST_FLAG:
                                return
                            md_dc_i = md_dc_ls[i]
                            self.model.objects.create(**md_dc_i)  # `md_i.save()`不太好, 容易覆盖原有数据
                            if tqdm_i:
                                tqdm_i.update(1)
                    except Exception as e:
                        if q is not None:
                            q.put(sys.exc_info())
                        else:
                            raise e

                from ..django.conf import db_engine
                use_sqlite3 = 'sqlite3' in db_engine
                if n < bulk_size or use_sqlite3:
                    for i in range(len(md_dc_ls)):
                        md_dc_i = md_dc_ls[i]
                        save_tqdm.update(1)
                        self.model.objects.create(**md_dc_i)                 # `md_i.save()`不太好, 容易覆盖原有数据
                    msg = f"{f_format}文件导入成功! 一共导入{df_rows}条数据, 耗时: {t_import.now(1)}秒."
                else:
                    a = np.arange(n)
                    s = slice(0, len(a), bulk_size)
                    start_end_ls = list(a[s])
                    thread_ls = []
                    for start_end_i in start_end_ls:
                        thread_i = threading.Thread(target=save_md_dc_ls, args=(md_dc_ls, start_end_i, start_end_i + bulk_size, n, save_tqdm, save_q))
                        thread_ls.append(thread_i)
                        thread_i.start()

                    # self.CREATE_EXIST_FLAG = False
                    self.check_thread_ls(thread_ls, save_q, 'CREATE_EXIST_FLAG')

                    # for thread_i in thread_ls:
                    #     thread_i.join()
                    msg = f"{f_format}文件导入中...<br>一共将导入{df_rows}条数据, <br>请稍后刷新查看是否完全导入."

                reset_db_sequence(self.model)
                self.message_user(request, msg)
                self.remove_temp_file(tempdir)

                return redirect("..")
        except Exception as e:
            msg = f"数据导入失败!</br>错误信息：&nbsp;" + str(e)

            ret_restful_api = request._post.get('ret_restful_api')  # 是否返回RestfulAPI格式

            from ..pure import convert_query_parameter_to_bool

            if not convert_query_parameter_to_bool(ret_restful_api):
                self.message_user(request, msg, level=messages.ERROR)
            else:
                return JsonResponse(data={
                    'status': 'error',
                    'msg': msg
                })

            _msg = msg
            _msg = _msg.replace('&nbsp;', ' ')
            _msg = _msg.replace('<br>', '\n')
            _msg = _msg.replace('</br>', '\n')
            if self.raise_error_to_debug:
                raise ImportError(f'\n\n ****** Import Data Error:\n\n{_msg}\n\n******************\n\n')
            else:
                print(f'\n\n ****** Import Data Error:\n\n{_msg}\n\n******************\n\n')
            return redirect("..")

        form = CsvImportForm()
        payload = {"form": form}
        return render(request, "admin/csv_form.html", payload)

    def check_thread_ls(self, thread_ls, q, flag_attr_name):
        from bdtime import tt
        while True:
            tt.sleep(0.1)
            if q.empty():
                count = 0
                for thread_i in thread_ls:
                    if thread_i.is_alive() == False:
                        count += 1
                if count == len(thread_ls):
                    break
                # if threading.active_count() == 1:
                #     break
            else:
                last = q.get()

                assert hasattr(self, flag_attr_name), f'check_thread_ls 不存在属性名[{flag_attr_name}]?'
                setattr(self, flag_attr_name, True)

                try:
                    raise Exception(f'{last[-2]}' if len(last) >= 2 else f'{last[-1]}')
                except:
                    raise Exception(last)
        print(u'end')

    def bulk_save(self, request, md_ls, f_format, df_rows, t_import, tempdir, batch_size=100):
        def _bulk_save():
            self.model.objects.bulk_create(md_ls, batch_size=batch_size)
            reset_db_sequence(self.model)
            self.message_user(request, f"{f_format}文件导入成功! 一共导入{df_rows}条数据, 耗时: {t_import.now(1)}秒.")
            self.remove_temp_file(tempdir)

        if df_rows < 3000:
            return _bulk_save()
        else:
            print('~~~ 多线程_bulk_save')
            self.message_user(request, f"{f_format}文件的{df_rows}条数据格式正确, 正在后台导入中, 请稍后查看...")
            t1 = threading.Thread(target=_bulk_save, args=())
            t1.start()

    def export_all_csv(self, request):
        # self.message_user(request, "成功导出全部数据为csv文件")
        if hasattr(self, 'export_as_csv') and self.export_all_fields_forever is False:
            ret = self.export_as_csv(request, queryset=self.model.objects.all(), model=self.model)
        else:
            ret = ExportCsvMixin().export_as_csv(request, queryset=self.model.objects.all(), model=self.model)
        return ret

    def export_all_excel(self, request):
        # self.message_user(request, "成功导出全部数据为csv文件")
        if hasattr(self, 'export_as_excel') and self.export_all_fields_forever is False:
            ret = self.export_as_excel(request, queryset=self.model.objects.all(), model=self.model)
        else:
            ret = ExportCsvMixin().export_as_excel(request, queryset=self.model.objects.all(), model=self.model)
        self.remove_temp_file(TEMPDIR)
        return ret

    def get_urls(self):
        my_urls = [
            path('import-csv/', self.import_csv),
            path('export_all_csv/', self.export_all_csv),
            path('export_all_excel/', self.export_all_excel),
        ]
        return my_urls + super().get_urls()

    def remove_temp_file(self, tempdir):
        return remove_temp_file(tempdir)

    def changelist_view(self, request, extra_context=None):
        if not self.check_import_and_export_perm:
            has_import_perm = has_export_perm = True
        else:
            opts = self.opts

            def has_action_permission(opts, action):
                codename = get_permission_codename(action, opts)
                has_perm = request.user.has_perm('%s.%s' % (opts.app_label, codename))
                return has_perm

            has_add_perm = has_action_permission(opts, 'add')
            has_change_perm = has_action_permission(opts, 'change')
            has_view_perm = has_action_permission(opts, 'view')

            has_import_perm = self.has_import_perm and has_add_perm and has_change_perm
            has_export_perm = self.has_export_perm and has_view_perm

        if extra_context is None:
            extra_context = {}
        extra_context.update({
            'custom_import_and_export_buttons': self.custom_import_and_export_buttons,
            'has_import_perm': has_import_perm,
            'has_export_perm': has_export_perm,
        })

        ret = super().changelist_view(request, extra_context=extra_context)
        return ret


class CsvImportExportAdmin(ImportAdmin, ExportCsvMixin):
    """
    CSV导入/导出Admin类

    - 不能与admin.ModelAdmin一起用!
    """

    actions = ['export_as_csv']


class ListDisplayMixin:
    def get_list_display(self, request):
        ret = super().get_list_display(request)
        if ret == ('__str__', ):
            meta = self.model._meta
            field_names = [field.name for field in meta.fields]
            ret = field_names
        return ret


class ExcelImportExportAdmin(ImportAdmin, ExportExcelMixin):
    """
    Excel导入/导出Admin类

    - 不能与admin.ModelAdmin一起用!
    """
    default_export_action = True        # 默认增加导出按钮

    def get_actions(self, request):
        ACTION_NAME = 'export_as_excel'
        if self.default_export_action and ACTION_NAME not in self.actions:
            if self.actions is None:
                self.actions = []
            self.actions.append(ACTION_NAME)
        ret = super().get_actions(request)
        return ret


class ListDisplayAdmin(ExcelImportExportAdmin):
    """
    * admin展示界面

    - 展示所有字段, 默认前两列为点击链接. 并去除'stop_field_ls'中的字段

    - stop_field_ls: 停用词列表, 字段名包含该词的字段将不展示.
        - 注意url和href的区别: url为本地路由; href超链接, 不显示
    """
    list_display = '__all__'        # 默认展示全部
    stop_field_ls = []              # 停用字段
    move_id_to_tail = False      # id移到最后一列去

    origin_list = False     # 展示原str

    add_first_field_to_link = False

    def __init__(self, *args, **kwargs):
        """
        增加一个可点击字段
        """
        super().__init__(*args, **kwargs)

        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        if self.list_display == [] or self.list_display is None:
            self.list_display = ('__str__', )
            self.origin_list = True
            return

        if self.add_first_field_to_link and self.list_display_links is not None and (not self.list_display_links) and len(field_names) >= 2:
            if field_names[0] == 'id':
                self.list_display_links = ('id', field_names[1])

        if (isinstance(self.list_display, str) and self.list_display == '__all__') or '__all__' in self.list_display:
            res = []
            for f in field_names:
                if f not in self.stop_field_ls:
                    res.append(f)
            self.list_display = res

        return

    def get_list_display(self, request):
        ret = super().get_list_display(request)
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        # model_str = self.model.__str__(self.model)
        # if not self.origin_list and ret == ('__str__',) and isinstance(model_str, str) and model_str.__contains__('ModelBase'):
        #     """如果用户没对list_display进行变更的话, 则自定义list_display字段"""
        #     meta = self.model._meta
        #     field_names = [field.name for field in meta.fields]
        #
        #     ret = []
        #     for f in field_names:
        #         if isinstance(f, str):
        #             # 如果有停用词, 则不加入ret中
        #             flag = False
        #             for r in self.stop_field_ls:
        #                 if f.__contains__(r):
        #                     flag = True
        #                     break
        #             if flag:
        #                 continue
        #         ret.append(f)

        if self.move_id_to_tail and 'id' in field_names and id not in self.stop_field_ls:
            ret.remove('id')
            ret.append('id')
        return ret


class ForceRunActionsAdmin(ListDisplayAdmin):
    """
    增加强制运行actions功能
    """
    def changelist_view(self, request, extra_context=None):
        """
        这里想跳过"必须选择一个数据"的确认框,
        但django原生admin可以, 而simpleui无法实现,
        经过改进后, 以"fc_"开头的方法将强制运行

        - https://stackoverflow.com/questions/4500924/django-admin-action-without-selecting-objects
        """
        MyModel = self.model

        # 强制运行以"fc_"开头的action
        if 'action' in request.POST and request.POST['action'].startswith('fc_'):
            if not request.POST.getlist(ACTION_CHECKBOX_NAME):
                post = request.POST.copy()
                for u in MyModel.objects.all():
                    post.update({ACTION_CHECKBOX_NAME: str(u.id)})
                request._set_post(post)
        return super().changelist_view(request, extra_context)


class PureAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        """
        这里想跳过"必须选择一个数据"的确认框,
        但django原生admin可以, 而simpleui无法实现,
        经过改进后, 以"fc_"开头的方法将强制运行

        - https://stackoverflow.com/questions/4500924/django-admin-action-without-selecting-objects
        """
        MyModel = self.model

        # 强制运行以"fc_"开头的action
        if 'action' in request.POST and request.POST['action'].startswith('fc_'):
            if not request.POST.getlist(ACTION_CHECKBOX_NAME):
                post = request.POST.copy()
                for u in MyModel.objects.all():
                    post.update({ACTION_CHECKBOX_NAME: str(u.id)})
                request._set_post(post)
        return super().changelist_view(request, extra_context)


class BaseAdmin(ForceRunActionsAdmin):
    """
    # 若search_term以变量prefix的值开头, 则检索最近xx条记录.
        - 如'~10'代表检索最近10条记录

    # 支持orm检索
    > 使用反引号[`]来替代引号["]
        - .filter(id__lt=20, wiki_id="asd")
        - .filter(wiki_id=`asd`).order_by(`-id`)[:3]
    """
    _tmp = None
    orm_executor = True     # 使用orm过滤器

    _ajax_search_term = None        # 用来ajax过滤
    _ajax_return_qs_ls = None       # 以便使用ajax方法返回的qs_ls

    def get_search_results(self, request, queryset, search_term):
        if not self.orm_executor:
            ret = super().get_search_results(request, queryset, search_term)
            return ret

        # --- 根据ajax方法返回qs_ls
        bd_ajax_return_qs_ls = '_ajax_return_qs_ls'
        if hasattr(self, bd_ajax_return_qs_ls) and getattr(self, bd_ajax_return_qs_ls) is not None:
            queryset = getattr(self, bd_ajax_return_qs_ls)
            setattr(self, bd_ajax_return_qs_ls, None)
            ret = (queryset, False)
            return ret

        # --- 根据orm语句进行过滤
        prefix = '~'  # 反向过滤~pk

        reg = re.compile(r'^\..*?[\)\]]$')  # 让.filter(xxx), .order_by(xxx)等orm语句可以执行

        if hasattr(self, '_ajax_search_term') and getattr(self, '_ajax_search_term'):
            search_term = self._ajax_search_term
            self._ajax_search_term = None

        if search_term and reg.match(search_term):
            print('search_term: ', search_term)
            from django.db.models import Q      # 不能删!!

            # html转义
            search_term = search_term.replace('`', '"')
            while ('=&' in search_term):     search_term = html.unescape(search_term)
            try:
                self._tmp = queryset
                exec(f'self._tmp = self._tmp{search_term}')
                queryset = self._tmp
                # exec(f'queryset = queryset{search_term}')     # 局部变量无法用exec赋值!
            except Exception as e:
                msg = f'orm语句执行出错! <br> search_term: {search_term},<br>  error: {e}'
                self.message_user(request, msg)
            ret = (queryset, False)
        elif search_term.startswith(prefix):
            try:
                if search_term.startswith(prefix):
                    search_term = search_term
                    search_term = int(search_term[len(prefix):])
            except Exception as e:
                raise TypeError(f'pk必须为整数! {e}')
            id_qsv_ls = queryset.values('pk')[:search_term]
            queryset = queryset.filter(pk__in=id_qsv_ls)
            ret = (queryset, False)
        else:
            ret = super().get_search_results(request, queryset, search_term)

        return ret
