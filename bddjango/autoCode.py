"""
autoCode
"""
from django.contrib import admin
from bddjango.adminclass import BaseAdmin, BulkDeleteMixin
from bddjango import get_field_names_by_model
from bddjango.adminclass import BaseAdmin
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType
from bddjango import convert_query_parameter_to_bool, my_api_assert_function
from bddjango import find_indexes_in_dc_ls


tmp_urls = None
tmp_views = None


def get_my_apps():
    my_apps = []

    from django.conf import settings
    install_apps = settings.INSTALLED_APPS
    import os
    app_path = './'
    for app_label in install_apps:
        if os.path.exists(os.path.join(app_path, app_label)):
            my_apps.append(app_label)
    return my_apps


my_apps = get_my_apps()


def get_layer_for_app_and_views():
    auto_dc_ls = []
    for app_label in my_apps:
        exec(f'global tmp_views; from {app_label} import views as tmp_views;')

        views = tmp_views
        func_ls = dir(views)

        s = 0
        vs = []
        for f in func_ls:
            md = getattr(views, f)
            if hasattr(md, 'queryset') and (
                    hasattr(md, 'serializer_class') or hasattr(md, 'list_fields') or hasattr(md,
                                                                                             'retrieve_fields')):
                if getattr(md, 'queryset') is not None and (
                        getattr(md, 'serializer_class') or getattr(md, 'list_serializer_class') or getattr(md,
                                                                                                           'auto_generate_serializer_class') or getattr(
                    md, 'retrieve_serializer_class')) or getattr(md, 'list_fields') or getattr(md,
                                                                                               'retrieve_fields'):
                    s += 1
                    v_i = f'{app_label}.{f}'
                    vs.append(v_i)
        if s != 0:
            dc = {
                app_label: vs
            }
            auto_dc_ls.append(dc)

    auto_apps = [list(auto_dc.keys())[0] for auto_dc in auto_dc_ls]

    default_views = []
    for auto_dc_i in auto_dc_ls:
        for k, v_ls in auto_dc_i.items():
            for v_i in v_ls:
                default_views.append(v_i)

    return auto_apps, auto_dc_ls, default_views


auto_apps, auto_dc_ls, default_views = get_layer_for_app_and_views()


def set_options(ls):
    options = []
    for o in ls:
        dc = {
            'key': o,
            'label': o
        }
        options.append(dc)
    ContentTypeAdmin.auto_wiki.layer['params'][0]['options'] = options


class ContentTypeAdmin(BaseAdmin):
    """
    # 自动生成代码和wiki的admin

    - 使用方式: admin.site.register(ContentType, ContentTypeAdmin)

    - 参数:
        - app_filter: app_label过滤器
    """

    app_filter = my_apps
    app_exclude = []

    list_filter = ['app_label']
    actions = ['auto_wiki', 'auto_code', 'auto_model']

    default_export_action = False
    custom_import_and_export_buttons = False  # 是否显示自定义的导入导出按钮
    has_import_perm = False  # 导入数据
    has_export_perm = False  # 全部导出

    default_use_complete_model_view = False  # 是否在`auto_code`中默认启用`增删改查`型`view`
    add_db_column = False  # 是否在`auto_model`中默认增加`db_column`

    codes_template_file_path = None

    def get_queryset(self, request):
        total_qs_ls = super().get_queryset(request)

        app_filter = self.app_filter
        if app_filter:
            total_qs_ls = total_qs_ls.filter(app_label__in=app_filter)

        app_exclude = self.app_exclude
        if app_exclude:
            total_qs_ls = total_qs_ls.exclude(app_label__in=app_exclude)

        app_label = request.GET.get('app_label')
        if app_label:
            _options = {}
            for dc in auto_dc_ls:
                key = list(dc.keys())[0]
                if key == app_label:
                    _options = dc
            if _options:
                _options = list(_options.values())[0]
            else:
                _options = []

            set_options(_options)
            ContentTypeAdmin.auto_wiki.layer['tips'] = f'请选择想要生成wiki的view_class, 限定app: {app_label}'
        else:
            set_options(default_views)
            ContentTypeAdmin.auto_wiki.layer['tips'] = '请选择一个想要生成wiki的view_class.'

        return total_qs_ls

    def auto_wiki(self, request, queryset=None, model=None):
        from bdtime import Time
        tt = Time()

        post = request.POST
        _view_class = post.get('view_class')

        if _view_class:
            app_label, view_class = _view_class.split('.')

            from bddjango.autoWiki import AutoWiki
            from django.test.client import ASGIRequest, FakePayload
            # 伪造一个request请求
            scope = {'type': 'http', 'http_version': '1.0', 'method': 'POST',
                     'path': '/api/admin/contenttypes/contenttype/ajax',
                     'raw_path': b'/api/admin/contenttypes/contenttype/ajax', 'root_path': '', 'scheme': 'http',
                     'query_string': b'app_label=author',
                     'headers': [(b'host', b'localhost:8000'), (b'connection', b'close'),
                                 (b'content-length', b'624'), (b'accept', b'application/json, text/plain, */*'), (
                                     b'user-agent',
                                     b'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'),
                                 (b'content-type',
                                  b'multipart/form-data; boundary=----WebKitFormBoundarym5HMNzwmAdbBBH3J'),
                                 (b'origin', b'http://10.120.65.140:2227'), (b'referer',
                                                                             b'http://10.120.65.140:2227/api/admin/contenttypes/contenttype/?app_label=author'),
                                 (b'accept-encoding', b'gzip, deflate'),
                                 (b'accept-language', b'zh-CN,zh;q=0.9,en;q=0.8'), (b'cookie',
                                                                                    b'fontSize=12; theme=/api/static/admin/simpleui-x/theme/e-blue-pro.css; theme_name=Enterprise%20blue%20pro; fold=false; adminer_key=07406eb2141d4cfdfc1d21fcd7a524fc; adminer_sid=5eb5495ff40b806d32f4b4ad8b4caeb7; MUIDB=3471AAE1567861750DD2BB71571E60CC; ckCsrfToken=VH4uNXIAYS3CG9cfJKHHhfzVj0yxJDwZTsw80Hls; token=dd95c297fe113b65516965ae6f09203c455210fd; UserInfo={%22id%22:12%2C%22username%22:%22test1234%22%2C%22nickname%22:%22%E6%B5%8B%E8%AF%95%E7%94%A8%E6%88%B7%22%2C%22email%22:%22%22%2C%22useriprelation_set%22:[]%2C%22groups%22:[]%2C%22is_staff%22:false%2C%22is_active%22:true%2C%22phone%22:null}; csrftoken=4rtE0HFNmMKiSg0MhKbiGZ976ZyT6NUcSdJGTGAuZ6uMGo2yTV0j8nEeSkJ47r2l; sessionid=eu5muzwony63cwdm9geh8jxm0bhcfi7j; tabstyle=raw-tab')],
                     'client': ['127.0.0.1', 48340], 'server': ['127.0.0.1', 8000], 'asgi': {'version': '3.0'}}

            scope.update(
                {
                    'method': 'GET',
                    'path': 'GET',
                    'query_string': f'&app_name={app_label}&view_class_name={view_class}&get_output_file={1}'
                }
            )

            body_file = FakePayload('')
            new_request = ASGIRequest(scope, body_file)

            response = AutoWiki.as_view()(new_request)
            assert response.status_code == 200, '`AutoWiki`返回码错误?'
            content = response.content.decode("utf-8")

            output_dirpath = 'media/tempdir/'
            import os
            os.makedirs(output_dirpath, exist_ok=True)

            output_filename = f'wiki__{_view_class}.txt'
            output_filepath = os.path.join(output_dirpath, output_filename)
            with open(output_filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            print('---------- autoWiki:')
            print(content)

            msg = f'成功生成wiki, 耗时: {tt.now(2)}秒. <br> <a href="/api/{output_filepath}" target="_blank">点击此处查看</a>'
            self.message_user(request, msg)

            from bddjango import remove_temp_file
            remove_temp_file(output_dirpath, MAX_TEMPS=20, desc='---')

        return JsonResponse(data={
            'status': 'success',
            'msg': f'处理成功! 耗时: {tt.now(2)}秒.'
        })

    auto_wiki.short_description = "生成Wiki"
    auto_wiki.icon = 'el-icon-upload'
    auto_wiki.type = 'success'
    auto_wiki.layer = {
        'title': '确定生成Wiki?',
        'tips': f'该操作可能比较耗时, 请耐心等候...',
        'params': [
            {
                # 这里的type 对应el-input的原生input属性，默认为input
                'type': 'select',
                # key 对应post参数中的key
                'key': 'view_class',
                # 显示的文本
                'label': 'view_class',
                'value': '',
                # 'parent_key': 'app_label',
                'options': [
                    {
                        'key': '0',
                        'label': '收入222'
                    },
                    {
                        'key': '1',
                        'label': '支出222'
                    }
                ]
            },
        ]
    }

    def auto_code(self, request, queryset=None, model=None):
        from bdtime import Time
        from bddjango import get_base_model
        from bddjango.autoWiki import AutoWiki
        import os
        from django.conf import settings
        from bddjango import replace_path_by_platform
        from bddjango import get_field_names_by_model
        import json
        from bddjango import get_field_type_in_py
        from copy import deepcopy

        tt = Time()

        post = request.POST

        use_complete_model_view = post.get('use_complete_model_view')
        use_complete_model_view = convert_query_parameter_to_bool(use_complete_model_view)
        print(f'~~~ use_complete_model_view: {use_complete_model_view}')

        _selected = post.get('_selected')
        if not _selected:
            return JsonResponse(data={
                'status': 'error',
                'msg': '请先选中数据！'
            })

        if ',' in _selected:
            return JsonResponse(data={
                'status': 'error',
                'msg': '一次只允许选中一条数据！'
            })

        checkbox = post.get('checkbox')
        content_type_i = self.model.objects.get(id=_selected)

        md_i = get_base_model(content_type_i)
        checkbox = checkbox.split(',') if checkbox else ['admin.py', 'urls.py', 'views.py']
        checkbox = [i.replace('.py', '') for i in checkbox]

        _codes_template_file_path = AutoWiki.path_of_jinja2_template
        _codes_template_file_path = os.path.join(
            os.path.dirname(replace_path_by_platform(AutoWiki.path_of_jinja2_template)), 'autoCode.html')

        codes_template_file_path = self.codes_template_file_path if self.codes_template_file_path else _codes_template_file_path
        my_api_assert_function(convert_query_parameter_to_bool(codes_template_file_path),
                               f'`codes_template_file_path`不能为空!')
        codes_template_file_path = replace_path_by_platform(codes_template_file_path)
        my_api_assert_function(os.path.exists(codes_template_file_path),
                               f'`codes_template_file_path`路径不存在![{codes_template_file_path}]')


        # region # --- 开始填充jinja模板
        from jinja2 import Template

        with open(codes_template_file_path, encoding='utf-8') as file_:
            template = Template(file_.read())

        tempdir_rootpath = 'media/tempdir'  # 临时输出文件的根目录
        output_dirpath = os.path.join(tempdir_rootpath, 'output')  # 临时输出文件的子目录
        os.makedirs(output_dirpath, exist_ok=True)
        output_f_suffix = '.txt'  # 使用`.md`打开太慢, `typora`会报错

        app_label = md_i._meta.app_label
        object_name = md_i._meta.object_name
        verbose_name = md_i._meta.verbose_name

        output_fname = 'codes__' + app_label + '_' + object_name + output_f_suffix

        output_fpath = os.path.join(output_dirpath, output_fname)
        if os.path.exists(output_fpath):
            os.remove(output_fpath)

        _fields = get_field_names_by_model(md_i, exclude_fields=['id'])

        field_dc_ls = []
        field_dc_i = {}
        _example_data = {}

        for f_name in _fields:
            # break
            f_type = get_field_type_in_py(md_i, f_name)
            if f_type in ['int', 'str']:
                f_value = 1 if f_type == 'int' else '"xxx"'  # 样例数据
                field_dc_i.update(
                    {
                        'f_name': f_name,
                        'f_type': f_type,
                        'f_value': f_value,
                    }
                )
                field_dc_ls.append(deepcopy(field_dc_i))
                _example_data.update({f_name: f_value})

            if len(field_dc_ls) >= 2:
                break

        example_data = json.dumps(_example_data)

        res_context_dc = {
            'app_label': app_label,
            'object_name': object_name,
            'verbose_name': verbose_name,
            'example_data': example_data,
            'use_complete_model_view': use_complete_model_view,
        }

        n = 2 if len(field_dc_ls) >= 2 else len(field_dc_ls)
        for i in range(n):
            res_context_dc.update(
                {
                    f'example_f_name_{i}': field_dc_ls[i].get('f_name'),
                    f'example_f_value_{i}': field_dc_ls[i].get('f_value'),
                }
            )

        for i in checkbox:
            res_context_dc.update({i: True})

        content = template.render(**res_context_dc)

        with open(output_fpath, 'w', encoding='utf-8') as f:
            f.write(content)

        print('\n---------- autoCodes:')
        print(content)

        msg = f'成功生成代码, 耗时: {tt.now(2)}秒. <br> <a href="/api/{output_fpath}" target="_blank">点击此处查看</a>'
        self.message_user(request, msg)

        from bddjango import remove_temp_file
        remove_temp_file(output_dirpath, MAX_TEMPS=20, desc='---')

        # endregion

        return JsonResponse(data={
            'status': 'success',
            'msg': f'处理成功! 耗时: {tt.now(2)}秒.'
        })

    auto_code.short_description = "代码生成"
    auto_code.icon = 'el-icon-upload'
    auto_code.type = 'success'
    auto_code.layer = {
        'title': '确定生成代码?',
        'tips': f'请选择将生成的代码:',
        'params': [
            {
                'type': 'checkbox',
                'key': 'checkbox',
                # 必须指定默认值
                # 'value': ['admin.py', 'urls.py', 'views.py'],
                'value': ['admin.py', 'urls.py', 'views.py'],
                'label': '代码类型',
                'options': [
                    # {
                    #     'key': '0',
                    #     'label': '全部'
                    # },
                    {
                        'key': '1',
                        'label': 'admin.py'
                    },
                    {
                        'key': '2',
                        'label': 'urls.py'
                    },
                    {
                        'key': '2',
                        'label': 'views.py'
                    },
                ]
            },
            {
                'type': 'switch',
                'key': 'use_complete_model_view',
                'label': '增删改查',
                'value': default_use_complete_model_view
            },
        ]
    }

    def auto_model(self, request, queryset):
        from bddjango.tools.generateModelCodeFromExcel import get_model_info
        import os
        from bdtime import tt
        import xlrd
        import pandas as pd
        from bddjango import convert_query_parameter_to_bool

        format_ls = ['xls', 'xlsx', 'csv']

        upload = request.FILES.get('upload')
        if not upload:
            return JsonResponse(data={
                'status': 'error',
                'msg': f'上传文件不能为空! 支持的文件格式为: {format_ls}'
            })

        f_format = upload._name.rsplit('.', 1)[-1]
        if f_format not in format_ls:
            return JsonResponse(data={
                'status': 'error',
                'msg': f'不支持的文件类型! 目前仅支持{format_ls}.'
            })

        post = request.POST
        add_db_column = post.get('add_db_column')
        add_db_column = convert_query_parameter_to_bool(add_db_column)
        print(f'~~~ add_db_column: {add_db_column}')

        tempdir = 'tempdir/auto_model'
        os.makedirs(tempdir, exist_ok=True)

        file_contents = upload.file.read()
        base_name, _ = os.path.splitext(upload._name)

        fname = upload._name
        f_path = os.path.join(tempdir, fname)

        if f_format == 'csv':
            try:
                encoding = 'utf-8'
                file_data = file_contents.decode(encoding)
            except Exception as e:
                print('-- 尝试用gbk编码 --')
                encoding = 'gbk'
                file_data = file_contents.decode(encoding)

            with open(f_path, 'w', encoding=encoding) as f:
                f.write(file_data)

            # # 为解决字段内有逗号导致分割错误问题, 只能采用pd了
            # df = pd.read_csv(fname, encoding=encoding)
        elif f_format == 'xls':
            wb = xlrd.open_workbook(file_contents=file_contents)
            df = pd.read_excel(wb)
            df.to_excel(f_path, index=False, encoding='utf-8')
        elif f_format == 'xlsx':
            try:
                wb = xlrd.open_workbook(file_contents=file_contents)
                df = pd.read_excel(wb)
                df.to_excel(f_path, index=False, encoding='utf-8')
            except Exception as e:
                raise TypeError(f'文件读入错误! 可转换为`xls`格式后重试. msg: {e}')

        model_info = get_model_info(f_path, add_db_column=add_db_column)
        content = model_info.get('model_code')
        output_fname = model_info.get('model_name')

        tempdir_rootpath = 'media/tempdir'  # 临时输出文件的根目录
        output_dirpath = os.path.join(tempdir_rootpath, 'output')  # 临时输出文件的子目录
        output_fpath = os.path.join(output_dirpath,
                                    f'{output_fname}_{tt.get_current_beijing_time_str(tt.common_date_time_formats.ms_int)}.txt')
        with open(output_fpath, 'w', encoding='utf-8') as f:
            f.write(content)

        print('\n---------- auto_model:')
        print(content)

        msg = f'成功生成模型代码, 耗时: {tt.now(2)}秒. <br> <a href="/api/{output_fpath}" target="_blank">点击此处查看</a>'
        self.message_user(request, msg)

        from bddjango import remove_temp_file
        remove_temp_file(tempdir, MAX_TEMPS=20, desc='--- tempdir')
        remove_temp_file(output_dirpath, MAX_TEMPS=20, desc='--- output_dirpath')

        return JsonResponse(data={
            'status': 'success',
            'msg': f'处理成功! 耗时: {tt.now(2)}秒.'
        })

    auto_model.short_description = '模型生成'
    auto_model.type = 'success'
    auto_model.icon = 'el-icon-upload'
    auto_model.enable = True

    auto_model.layer = {
        'params': [
            {
                'type': 'file',
                'key': 'upload',
                'label': '数据文件'
            },
            {
                'type': 'switch',
                'key': 'add_db_column',
                'label': 'db列名',
                'value': add_db_column
            },
        ]
    }


def register_content_type_admin(app_filter=None, app_exclude=None, list_filter=None,
                                default_use_complete_model_view=None, add_db_column=None):
    """
    自动注册content_type_admin

    :param app_filter: app过滤列表
    :param app_exclude: app排除列表
    :param list_filter: 过滤字段
    :param default_use_complete_model_view: 是否在`auto_code`中默认启用`增删改查`型`view`
    :param add_db_column: 是否在`auto_model`中默认增加`db_column`

    --- eg:
    >>>　register_content_type_admin(default_use_complete_model_view=1, add_db_column=0)
    """
    if app_filter is not None:
        ContentTypeAdmin.app_filter = app_filter
    if app_exclude is not None:
        ContentTypeAdmin.app_exclude = app_exclude
    if list_filter is not None:
        ContentTypeAdmin.list_filter = list_filter
    if default_use_complete_model_view is not None:
        default_use_complete_model_view = convert_query_parameter_to_bool(default_use_complete_model_view)
        ContentTypeAdmin.default_use_complete_model_view = default_use_complete_model_view
        params = ContentTypeAdmin.auto_code.layer['params']
        indexes = find_indexes_in_dc_ls(params, 'key', 'use_complete_model_view')
        assert len(indexes) == 1, 'ContentTypeAdmin.layer重置`use_complete_model_view`出错'
        params[indexes[0]]['value'] = default_use_complete_model_view
    if add_db_column is not None:
        add_db_column = convert_query_parameter_to_bool(add_db_column)
        ContentTypeAdmin.add_db_column = add_db_column
        params = ContentTypeAdmin.auto_model.layer['params']
        indexes = find_indexes_in_dc_ls(params, 'key', 'add_db_column')
        assert len(indexes) == 1, 'ContentTypeAdmin.layer重置`add_db_column`出错'
        params[indexes[0]]['value'] = add_db_column
    admin.site.register(ContentType, ContentTypeAdmin)
