"""
导入csv
导出csv或excel
"""
import csv
import datetime
import threading
import numpy as np
import pandas as pd
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

from .. import get_model_max_id_in_db
from .. import reset_db_sequence


# --- 初始化环境 ---
from .admin_env_init import CHANGE_LIST_HTML_PATH


class IDAdmin(admin.ModelAdmin):
    """
    * 保存时自动处理id, 解决postgre在批量导入数据后的主键冲突问题.

    - 该方法仅对admin界面手动保存时调用的save_model()方法生效, 不影响obj.save()方法效率.
    """

    def save_model(self, request, obj, form, change):
        """
        参数change分辨保存or修改.
        若为保存, 则model的id值自动更新为数据库中最大id+1.
        """
        if change is False:
            # meta = obj._meta
            # obj.id = get_model_max_id_in_db(model=None, meta=meta)
            obj.id = get_model_max_id_in_db(model=obj)
        obj.save()


from pandas._libs.tslibs.timestamps import Timestamp


# --- 处理df中的特殊格式
def conv_date_field_str_format(ts):
    """
    DateField的格式转换

    - 将csv中的时间字符转为符合django的时间格式
    """
    if isinstance(ts, Timestamp):
        return ts

    if not ts or ts == 'None':
        return None

    if isinstance(ts, float) and np.isnan(ts):
        return None

    if '/' in ts:
        ts = datetime.datetime.strptime(ts, '%Y/%m/%d')
        ts = datetime.datetime.strftime(ts, '%Y-%m-%d')
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

    def bulk_delete(self, request, queryset=None, model=None):
        t_delete = Time()
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"成功删除{count}条数据, 耗时: {t_delete.now(1)}秒.")

    bulk_delete.short_description = "批量删除"
    bulk_delete.icon = 'el-icon-delete'


class ExportExcelMixin:
    export_asc = False      # 按id升序导出

    def export_as_excel(self, request, queryset=None, model=None):
        if model is None:
            meta = self.model._meta
        else:
            meta = model._meta

        field_names = [field.name for field in meta.fields]
        verbose_names = [field.verbose_name for field in meta.fields]

        response = HttpResponse(content_type='application/msexcel')
        filename = urlquote(f"{meta.verbose_name}.xlsx")
        response['Content-Disposition'] = f'attachment; filename={filename}'
        wb = Workbook()
        ws = wb.active

        if self.export_asc:
            if queryset.count() and hasattr(queryset[0], 'id'):
                queryset = queryset.order_by('id')

        ws.append(verbose_names)
        for obj in queryset:
            data = [f'{getattr(obj, field)}' for field in field_names]
            ws.append(data)
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
                    df = pd.read_csv(fname, encoding=encoding)
                elif f_format in ['xlsx', 'xls']:
                    wb = xlrd.open_workbook(file_contents=read_data)
                    df = pd.read_excel(wb)
                else:
                    df = None
                df_rows = df.shape[0]        # 一共多少行数据
                titles = df.columns.tolist()

                meta = self.model._meta
                field_names = [field.name for field in meta.fields]
                verbose_names = [field.verbose_name for field in meta.fields]
                field_dc = dict(zip(verbose_names, field_names))

                title_ls = [field_dc.get(title_i) if field_dc.get(title_i) else title_i for title_i in titles]

                curr_id = get_model_max_id_in_db(self.model)

                df1 = df.copy()
                df1.columns = title_ls

                md_ls = []
                for index, row in df1.iterrows():
                    content_ls = row.values.tolist()

                    # 处理DateField字段
                    for i in range(len(title_ls)):
                        title_i = title_ls[i]
                        content_ls[i] = conv_nan(content_ls[i])

                        attr = getattr(self.model, title_i)
                        if not hasattr(attr, 'field'):
                            continue
                        attr_field_name = attr.field.__class__.__name__

                        if attr_field_name in ['DateField', 'DateTimeField']:
                            # print(i, title_i, content_ls[i])
                            if attr_field_name == 'DateTimeField':
                                res = conv_date_time_field_str_format(ts=content_ls[i])
                                if res is None:
                                    print(content_ls[i])
                                content_ls[i] = res
                            else:
                                ts = content_ls[i]
                                res = conv_date_field_str_format(ts=ts)
                                if res is None:
                                    print(content_ls[i])
                                content_ls[i] = res

                    dc = dict(zip(title_ls, content_ls))
                    dc.update({'id': curr_id})
                    curr_id += 1
                    md = self.model(**dc)
                    md_ls.append(md)
                    # self.model.objects.create(**dc)
                # from bddjango.django import get_model_base
                # get_model_base(self.model)
                self.model.objects.bulk_create(md_ls)
                reset_db_sequence(self.model)
                self.message_user(request, f"{f_format}文件导入成功! 一共导入{df_rows}条数据, 耗时: {t_import.now(1)}秒.")
                self.remove_temp_file(tempdir)
                return redirect("..")
        except Exception as e:
            self.message_user(request, f"第 {index+1} 条数据导入失败!</br>错误信息：&nbsp;" + str(e), level=messages.ERROR)
            return redirect("..")

        form = CsvImportForm()
        payload = {"form": form}
        return render(request, "admin/csv_form.html", payload)

    def export_all_csv(self, request):
        # self.message_user(request, "成功导出全部数据为csv文件")
        return ExportCsvMixin().export_as_csv(request, queryset=self.model.objects.all(), model=self.model)

    def export_all_excel(self, request):
        # self.message_user(request, "成功导出全部数据为csv文件")
        return ExportExcelMixin().export_as_excel(request, queryset=self.model.objects.all(), model=self.model)

    def get_urls(self):
        my_urls = [
            path('import-csv/', self.import_csv),
            path('export_all_csv/', self.export_all_csv),
            path('export_all_excel/', self.export_all_excel),
        ]
        return my_urls + super().get_urls()

    def remove_temp_file(self, tempdir):
        # 内存清理
        temps = len(os.listdir(tempdir))
        MAX_TEMPS = 5
        if temps > MAX_TEMPS:
            t1 = threading.Thread(target=ImportAdmin._remove_temp_file, args=(tempdir, MAX_TEMPS, ))
            t1.start()
        else:
            print(f'...excel缓存还足够, 不用清理... 缓存容量: {temps}/{MAX_TEMPS}')
        return

    @staticmethod
    def _remove_temp_file(tempdir, MAX_TEMPS=5):
        # --- 清理缓存, 清空tempdir下的所有文件
        fpath_ls = os.listdir(tempdir)
        temps = len(fpath_ls)

        if temps < MAX_TEMPS:
            print(f'...缓存还足够, 不用清理... 缓存容量: {temps}/{MAX_TEMPS}')
            return
        tt = Time()

        tt.sleep(1)
        print('*************** 开始清理缓存 *************')
        for fpath in fpath_ls:
            i = 0
            tt.__init__()
            while tt.during(5):
                i += 1
                dirpath = os.path.join(tempdir, fpath)
                try:
                    os.remove(dirpath)
                    print(f"~~~ success: 移除文件[{dirpath}]成功! -- 第[{i}]次")
                    break
                except:
                    print(f"** 第[{i}]次移除文件[{dirpath}]失败...")
                    tt.sleep(1)
                    if i > 5:
                        print(f"======== Warning: 移除文件[{dirpath}]失败!")
        print('*************** 缓存清理完毕 *************')


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

    # actions = ['export_as_excel']
    def __init__(self, *args, **kwargs):
        if 'export_as_excel' not in self.actions:
            self.actions.append('export_as_excel')
        super().__init__(*args, **kwargs)

    def get_search_results(self, request, queryset, search_term):
        """
        * 若search_term以变量prefix的值开头, 则检索最近xx条记录.

        - 如'~10'代表检索最近10条记录
        """
        prefix = '~'
        if search_term is not None and not search_term.startswith(prefix):
            ret = super().get_search_results(request, queryset, search_term)
        else:
            try:
                if search_term.startswith(prefix):
                    search_term = search_term
                    search_term = int(search_term[len(prefix):])
            except:
                raise TypeError('id必须为整数!')
            id_qsv_ls = queryset.values('id')[:search_term]
            queryset = queryset.filter(id__in=id_qsv_ls)
            ret = (queryset, False)
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
    # search_fields = ['id', ]
    # list_per_page = 10

    origin_list = False     # 展示原str

    def __init__(self, *args, **kwargs):
        """
        增加一个可点击字段
        """
        super().__init__(*args, **kwargs)

        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        if self.list_display == [] or self.list_display == None:
            self.list_display = ('__str__', )
            self.origin_list = True
            return

        if not self.list_display_links and len(field_names) >= 2:
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


def list_display_admin_register(cls):
    """
    * 类装饰器, 未完待续.
    """
    return cls


class BaseAdmin(ListDisplayAdmin):
    pass

