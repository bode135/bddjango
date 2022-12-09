from django.http import JsonResponse
from django.contrib import admin


class InitImportDataMixin:
    """
    导出初始数据的action_mixin

    - init_import_data_f_path: 需要导入的excel文件路径, 默认为`./docs/{self.model._meta.verbose_name}.xlsx
    """
    init_import_data_f_path = None

    @admin.action(permissions=['add'])
    def init_import_data(self, request, queryset=None, model=None):
        from bdtime import Time
        tt = Time()

        count = self.model.objects.count()

        if count != 0:
            msg = '初始化数据时, count必须为0! 请先清空数据!'
            return JsonResponse(data={
                'status': 'error',
                'msg': msg
            })

        from django.test import Client
        import os

        meta = self.model._meta

        from django.contrib import messages
        import json

        # --- 获取初始表格的文件路径
        f_path = self.init_import_data_f_path
        if f_path is None:
            f_path = os.path.join('media', f'init_data/{meta.verbose_name}.xls')
            # f_path = os.path.join(os.path.dirname(__file__), f'docs/{meta.verbose_name}.xlsx')

        # assert os.path.exists(f_path), f'初始表格数据路径错误: f_path[{f_path}]不存在!'

        if not os.path.exists(f_path):
            msg = f'初始表格数据路径错误: f_path[{f_path}]不存在!'
            return JsonResponse(data={
                'status': 'error',
                'msg': f'导入失败! msg: {msg}'
            })

        with open(f_path, 'rb') as f:
            # files = {'csv_file': f}

            c = Client()
            url = f'/api/admin/{meta.app_label}/{meta.model_name}/import-csv/'
            success = True
            try:
                data = {
                    'ret_restful_api': 1,
                    'csv_file': f
                }
                response = c.post(url, data=data)       # c.post(url, data=files)
                print('response.status_code --- ', response.status_code)
                print('response.content --- ', response.content.decode('utf-8'))

                if not response.content:
                    count_1 = self.model.objects.count()
                    self.message_user(request, f"成功导入{count_1}条数据, 耗时: {tt.now(2)}秒.")
                    return JsonResponse(data={
                        'status': 'success',
                        'msg': '操作完成, 导入结果: [导入成功]'
                    })
                resp_1 = json.loads(response.content)
                if resp_1.get('status') == 'error':
                    self.message_user(request, f"导入失败! msg:<br>{resp_1.get('msg')}", level=messages.ERROR)
                    # return JsonResponse(data=resp_1)
                    self._ajax_return_qs_ls = self.model.objects.all()
                    return JsonResponse(data={
                        'status': 'success',
                        'msg': f'执行完毕, 导入结果: [导入失败]'
                    })
            except Exception as e:
                success = False
                msg = f'处理失败: {e}'

            if not success:
                return JsonResponse(data={
                    'status': 'error',
                    'msg': msg
                })

        count_1 = self.model.objects.count()
        self.message_user(request, f"成功导入{count_1}条数据, 耗时: {tt.now(2)}秒.")

        return JsonResponse(data={
            'status': 'success',
            'msg': f'处理成功! 耗时: {tt.now(2)}秒.'
        })

    init_import_data.short_description = "导入初始数据"
    init_import_data.icon = 'fa fa-spinner'
    init_import_data.confirm = '确定导入初始数据？'
    init_import_data.layer = {
        'title': '确定导入初始数据?',
        'tips': '该操作可能比较耗时, 请耐心等候...',
    }
