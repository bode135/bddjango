from bddjango import APIView, APIResponse, my_api_assert_function, get_list, Time
from django.test import Client
import json
from . import models
from bddjango import CompleteModelView
from django.shortcuts import render
from bddjango import get_field_names_by_model
from bddjango.baseSearchView import BaseFullTextSearchMixin
import os


def get_file_content_with_encoding(path):
    try:
        with open(path, encoding='utf-8') as file:
            content = file.read()
    except:
        with open(path, encoding='gbk') as file:
            content = file.read()
    return content


class Doc(APIView):
    def get(self, request, *args, **kwargs):
        import re

        request_data = request.GET
        output_filepath = request_data.get('output_filepath')

        content = get_file_content_with_encoding(output_filepath)

        print(content)

        reg = re.compile(r'\|\n+\|')
        content = reg.sub(r'|\n|', content)

        reg = re.compile(r'\n+>')
        content = reg.sub(r'\n>', content)

        reg = re.compile(r'\<pk\>')
        content = reg.sub('&lt;pk&gt;', content)

        context = {
            'article_content': content,
        }
        ret = render(request, "copyCode.html", context=context)
        return ret


class ImportExportData(APIView):
    """
    导入导出数据

    POST http://127.0.0.1:8000/api/file_upload/ImportExportData/    # 导出`法律资源表`
    {
        "option_type": "export_data",
        "table": "Law",
        "export_ordering": ["id"],
        "_selected_action": [1, 2, 3]
    }

    POST http://127.0.0.1:8000/api/index/ImportExportData/         # 查第一页的`国外法规`, 并获取统计字典
    {
        "option_type": "import_data",
        "file": "附带的文件",
        "table": "Book"
    }
    """
    model_dc = None

    client = Client()

    def get_model_dc(self):
        """
        避免从其它app导入model时出现循环导入问题
        """
        return self.model_dc

    def get(self, request, *args, **kwargs):
        request_data = request.GET
        model_dc = self.get_model_dc()
        ret = ImportExportData.export_data(request_data, model_dc, self.client)
        return ret

    def post(self, request, *args, **kwargs):
        request_data = request.data

        option_type = request_data.get('option_type', 'export_data')
        option_types = ['export_data', 'import_data']
        my_api_assert_function(option_type in option_types, f'option_type取值范围: {option_types}')

        model_dc = self.get_model_dc()

        if option_type == 'export_data':
            ret = ImportExportData.export_data(request_data, model_dc, self.client)
        else:
            ret = ImportExportData.import_data(request_data, model_dc, self.client)
        return ret

    @staticmethod
    def export_data(request_data, model_dc, client):
        table = request_data.get('table')
        my_api_assert_function(table is not None, '`table`字段不能为空!')
        my_api_assert_function(table in model_dc, f'`table`的取值范围: {list(model_dc.keys())}')

        model_class = model_dc.get(table)
        meta = model_class._meta

        url = f'/api/admin/{meta.app_label}/{meta.model_name}/export_all_excel/'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        _selected_action = get_list(request_data, '_selected_action')
        export_ordering = get_list(request_data, 'export_ordering')

        data = {}
        if export_ordering:
            data.update({'export_ordering': export_ordering})
        if _selected_action:
            data.update({'_selected_action': _selected_action})

        # response = c.post(url, data=json.dumps(payload), headers=headers)
        response = client.post(url, data=data, headers=headers)
        return response

    @staticmethod
    def import_data(request_data, model_dc, client):
        msg = 'ok'
        status = 200
        tt = Time()

        table = request_data.get('table')
        my_api_assert_function(table is not None, '`table`字段不能为空!')
        my_api_assert_function(table in model_dc, f'`table`的取值范围: {list(model_dc.keys())}')
        model_class = model_dc.get(table)
        meta = model_class._meta

        file = request_data.get('file')
        my_api_assert_function(file is not None, '`file`字段不能为空!')

        count_0 = model_class.objects.count()

        url = f'/api/admin/{meta.app_label}/{meta.model_name}/import-csv/'
        data = {
            'ret_restful_api': 1,
            'csv_file': file
        }
        response = client.post(url, data=data)  # c.post(url, data=files)
        if response.content:
            resp_dc = json.loads(response.content.decode('utf-8'))
            if resp_dc.get('status') == 'error':
                msg = f'导入失败! error: {resp_dc.get("msg")}'
                status = 404
        else:
            count_1 = model_class.objects.count()
            msg = f"成功导入{count_1 - count_0}条数据, 耗时: {tt.now(2)}秒."
        return APIResponse(ret=None, msg=msg, status=status)


class FileSelection(CompleteModelView):
    """
    上传路径选项

    POST /api/file_upload/FileSelection/    # 增
    {
        "name": "xxx",
        "path": "xxx"
    }
    DELETE /api/file_upload/FileSelection/1/    # 删
    PUT /api/file_upload/FileSelection/1/      # 改, 携带数据的格式和POST一样

    GET /api/file_upload/FileSelection/    # 查, 列表页
    GET /api/file_upload/FileSelection/1/    # 查, 详情页
    """
    queryset = models.FileSelection


class UploadFile(CompleteModelView):
    """
    上传文件管理

    POST /api/file_upload/UploadFile/    # 增
    {
        "title": "xxx",
        "replace_path": "xxx"
    }
    DELETE /api/file_upload/UploadFile/1/    # 删
    PUT /api/file_upload/UploadFile/1/      # 改, 携带数据的格式和POST一样

    GET /api/file_upload/UploadFile/    # 查, 列表页
    GET /api/file_upload/UploadFile/1/    # 查, 详情页
    """
    queryset = models.UploadFile


class DownLoadFile(APIView):
    """
    下载指定路径的文件

    GET http://10.120.65.140:2240/api/file_upload/DownLoadFile/?download_file_path=/opt/server/media/test/download.zip
    """
    def get(self, request, *args, **kwargs):
        request_data = request.GET

        download_file_path = request_data.get('download_file_path')
        assert os.path.isfile(download_file_path), '`download_file_path`不能为文件夹!'

        # --- 返回文件流
        def file_iterator(file_name, open_model='rb', chunk_size=512):
            with open(file_name, open_model) as f:  # , encoding=encoding
                while True:
                    c = f.read(chunk_size)
                    if c:
                        yield c
                    else:
                        break

        from django.http import StreamingHttpResponse
        from django.utils.http import urlquote
        # urlquote("/opt/server/media/test")

        download_file_name = os.path.basename(download_file_path)
        response = StreamingHttpResponse(file_iterator(download_file_path))
        # response['Content-Type'] = 'application/octet-stream'
        filename = urlquote(download_file_name)
        response['Content-Type'] = 'application/x-zip-compressed'
        response['Content-Disposition'] = 'attachment;filename="{0}"'.format(filename)

        return response


class Search(BaseFullTextSearchMixin, CompleteModelView):
    """
    测试基于orm的全文检索功能

    /api/file_upload/Search/
    """
    queryset = models.UploadFile
    list_fields = get_field_names_by_model(queryset) + ['search_rank']


class WebSSH(APIView):
    """
    WebSSH

    GET http://10.120.65.140:2240/api/file_upload/WebSSH/
    """

    super_username_ls = ['superadmin', 'superuser']

    my_des = None

    def get(self, request, *args, **kwargs):
        from django.shortcuts import HttpResponseRedirect
        from tools.my_des import MyDes
        from time import time

        # user = request.user
        # my_api_assert_function(user.username in self.super_username_ls, '权限不够', 403)

        if self.my_des is None:
            self.my_des = MyDes('TESTKEY2')

        # message = {"username": "root", "password": "passwd", "hostname": "10.120.65.140", "port": 22240,
        #            "time": time() * 1000}
        message = {"username": "root", "password": "passwd", "hostname": "localhost", "port": 22,
                   "time": time() * 1000}
        msg_str = json.dumps(message)
        ct = self.my_des.encrypt(msg_str)
        return HttpResponseRedirect(f'/api/webssh/?ct={ct}')

