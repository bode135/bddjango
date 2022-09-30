"""
解析introduction, 自动生成.md

- 示例:
```
标题
- 这一定是简介, 没有的话, 简介就是标题

GET /api/authors/InstitutionType/   # 接口, 可能会在最前方指明请求类型[GET, POST]
POST /api/authors/InstitutionType/      # 注明POST方法的话, 会将后面携带的dict加上
{
    "请求数据": "xxx"
}
```

"""


import os
import sys
from jinja2 import Template
from bdtime import tt

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.core.cache import cache
from rest_framework.request import Request
from rest_framework.views import APIView

from .django import APIResponse, BaseListView, api_decorator
from .MultipleConditionSearch import AdvancedSearchView
from .django import convert_db_field_type_to_python_type
from .pure import convert_query_parameter_to_bool
from .django import get_base_serializer
from .django import my_api_assert_function


global tmp


RLT_PATH_OF_JINJIA2_TEMPLATE = 'templates\\autoWiki.html'       # 使用`jinja2`模板来生成`wiki`模板
ABS_PATH_OF_JINJIA2_TEMPLATE = os.path.join(os.path.dirname(__file__), RLT_PATH_OF_JINJIA2_TEMPLATE)


class AutoWiki(APIView):
    """
    自动生成wiki文档

    - app_name: 目标app, 必填
    - view_class_name: 目标view, 可空
    - ret_all_fields: 是否返回全部字段, 默认False
    - ADD_CAN_BE_EMPTY: 增加“能否为空”字段, 默认False
    - get_output_file: 下载文件, 仅能下一个*view_class*的说明文档, 适合*linux*服务端上使用

    - `.md`备注方法
        {#[*]( "这是注释")#}
        {#[ ]( "最好写上 [GET POST] 等")#}
    """

    open_output_txt_file = True     # `win`在运行完成后, 打开输出的`txt`文件
    path_of_jinja2_template = ABS_PATH_OF_JINJIA2_TEMPLATE       # 使用`jinja2`模板来生成`wiki`模板

    # response_render_format = {
    #     'status': 'code',
    #     'msg': 'message',
    #     'result': 'data',
    # }
    ret_dc = {
        'status': 200,
        'msg': 'ok',
        'result': {
            'page_dc': {
                'count_items': 10,
                'total_pages': 1,
                'page_size': 3,
                'p': 1,
            },
            'data': None,
        },
    }

    def get(self, request, *args, **kwargs):
        """自动生成wiki文档"""
        res_context_dc = {}     # 将结果变量储存为文本字典, 好用`jinja2`来填写模板

        ret = []
        request_data = request.GET

        # --- 必填
        app_name = request_data.get('app_name')
        # assert app_name, 'app_name不能为空!'
        my_api_assert_function(app_name, 'app_name不能为空!')

        # --- 选填
        view_class_name = request_data.getlist('view_class_name')       # 可空
        ret_all_fields = request_data.getlist('ret_all_fields', False)     # 返回全部字段 or 只保留serializer_fields中返回的字段
        ADD_CAN_BE_EMPTY = request_data.getlist('ADD_CAN_BE_EMPTY', False)   # 增加“能否为空”字段
        SLEEP_TIME = request_data.get('SLEEP_TIME', 0.2)    # sleep时间, 也就是文件保存到打开的间隔
        MAX_LEN = request_data.get('MAX_LEN', 100)      # 示例数据最长字段限制

        exec(f'global tmp; from {app_name} import views as tmp;')        # 执行
        print('---------', tmp)

        views = tmp
        func_ls = dir(views)

        s = 0
        vs = []
        for f in func_ls:
            md = getattr(views, f)
            if hasattr(md, 'queryset') and (hasattr(md, 'serializer_class') or hasattr(md, 'list_fields') or hasattr(md, 'retrieve_fields')):
                print('---------', f, md)
                if getattr(md, 'queryset') is not None and (getattr(md, 'serializer_class') or getattr(md, 'list_serializer_class') or getattr(md, 'auto_generate_serializer_class') or getattr(md, 'retrieve_serializer_class')) or getattr(md, 'list_fields') or getattr(md, 'retrieve_fields'):
                    if not view_class_name or f in view_class_name:
                        s += 1
                        print(f, md)
                        vs.append([f, md])
        print(s)
        if s == 0:
            msg = '没有任何可以转换的view_class! 将自动生成!!'
            return APIResponse(None, status=404, msg=msg)

        print('--------------------------------------------------------------------------')

        """生成一个view的wiki文档"""

        """生成一个view的wiki文档"""
        from bddjango.django import get_base_model
        from django.forms import model_to_dict
        from bddjango import show_json
        from bddjango.django import get_field_type_in_py
        from bddjango import create_dir_if_not_exist, create_file_if_not_exist
        import re
        import json
        import os

        tempdir_rootpath = 'tempdir'        # 临时输出文件的根目录
        output_dirpath = os.path.join(tempdir_rootpath, 'output')       # 临时输出文件的子目录
        create_dir_if_not_exist(tempdir_rootpath)
        create_dir_if_not_exist(output_dirpath)

        path_of_jinja2_template = request_data.get('path_of_jinja2_template', self.path_of_jinja2_template)

        # region # --- 循环获取view的文档

        for view_id in range(len(vs)):
            # view_id = 0       # debug
            # issubclass(v, BaseListView)

            # --- 获取单个view的名称和实例
            fv = vs[view_id]
            f, v = fv       # view_class_name, view_class_instance

            # --- 输出文件的路径
            output_f_suffix = '.txt'        # 使用`.md`打开太慢, `typora`会报错
            # output_f_suffix = '.md' if path_of_jinja2_template else '.txt'

            output_fname = f + output_f_suffix
            output_fname = os.path.join(output_dirpath, output_fname)
            if os.path.exists(output_fname):
                os.remove(output_fname)

            def output_to_file_and_prt(text='', output_fname=output_fname, show_in_console=False):

                output_file = open(output_fname, 'a+', encoding='utf-8')

                if show_in_console:
                    print(text)
                print(text, file=output_file)
                output_file.close()

            # --- 开始写入

            output_to_file_and_prt('****************')
            res_context_dc['introduction'] = v.__doc__      # context: 简介
            output_to_file_and_prt(res_context_dc['introduction'])

            output_to_file_and_prt('****************')
            output_to_file_and_prt()

            output_to_file_and_prt(f'\n=======  {view_id}  =========  \n')
            res_context_dc['view_id'] = str(view_id)  # context: view_id

            view_class_name, view_class_instance = f, v
            output_to_file_and_prt(f'---, view_class_name: [{view_class_name}], view_class_instance: [{view_class_instance}]')
            res_context_dc['view_class_name'] = str(view_class_name)     # context: view_class_name
            res_context_dc['view_class_instance'] = str(view_class_instance)     # context: view_class_instance

            output_to_file_and_prt()

            # --- 获取model和meta
            md = get_base_model(v.queryset)
            meta = md._meta

            url = f'/api/{app_name}/{f}/'

            output_to_file_and_prt('------------ 请求URL')
            output_to_file_and_prt(f"`{url}`")
            res_context_dc['request_url'] = str(url)     # context: 请求URL

            output_to_file_and_prt()

            filter_fields = None
            if hasattr(v, 'filter_fields'):
                if v.filter_fields:
                    output_to_file_and_prt('------------ 过滤字段')
                    output_to_file_and_prt(f"`{v.filter_fields}`")

                    filter_fields = v.filter_fields
                    if filter_fields == []:
                        filter_fields = None

                    res_context_dc['filter_fields'] = str(v.filter_fields)  # context: 请求URL
                    output_to_file_and_prt()

            # 确定serializer_class, 以免报错
            v.serializer_class = v.serializer_class or v.retrieve_serializer_class or v.list_serializer_class

            # --- 获取field_name和verbose_name

            field_names = [field.name for field in meta.fields]
            verbose_names = [field.verbose_name for field in meta.fields]
            can_be_empty_ls = [field.null and field.blank for field in meta.fields]

            field_type_ls = [get_field_type_in_py(md, field_name) for field_name in field_names]
            # field_type = get_field_type_in_py(md, field_name)

            if hasattr(v, 'auto_generate_serializer_class') and v.auto_generate_serializer_class:
                # from bddjango import get_base_serializer
                # v: BaseListView
                v__serializer_class = v().get_serializer_class()
                # v__queryset = get_base_model(v().get_queryset()).objects.all()
                # v__serializer_class(v__queryset, many=True).data
                # v__serializer_class.__dict__.get('_declared_fields')
                v.serializer_class = v__serializer_class

            if not v.serializer_class:
                list_serializer_class = retrieve_serializer_class = None
                if hasattr(v, 'list_fields'):
                    list_fields = getattr(v, 'list_fields')
                    list_serializer_class = get_base_serializer(v.queryset, list_fields)

                if hasattr(v, 'retrieve_fields'):
                    retrieve_fields = getattr(v, 'retrieve_fields')
                    retrieve_serializer_class = get_base_serializer(v.queryset, retrieve_fields)
                v.serializer_class = list_serializer_class or retrieve_serializer_class

            # --- 把serializers里面的拓展字段通过__doc__转义后加进field_names
            serializer_field_ls = v.serializer_class.__dict__.get('_declared_fields')
            text = v.serializer_class.__doc__ or ""

            for serializer_field_i, field_type_i in serializer_field_ls.items():
                print(serializer_field_i, field_type_i)
                reg = re.compile(f'^.*{serializer_field_i}: +(.*?) *$', re.M)
                match = reg.search(text)
                if match:
                    verbose_name_i = match.group(1)
                else:
                    verbose_name_i = serializer_field_i

                _conved_flag = False
                if isinstance(serializer_field_i, str) and '__' in serializer_field_i:
                    fk_model_name, fk_field_name = serializer_field_i.split('__', 1)
                    # print('--- 序列化自动生成的字段: ', fk_model_name, fk_field_name)
                    if fk_model_name in field_names and '__' not in fk_field_name:
                        _meta_field = meta.fields[field_names.index(fk_model_name)]
                        # to_field = _meta_field.to_fields[0]
                        # to_field = to_field if to_field else 'pk'
                        _field_value = getattr(md, fk_model_name)
                        from .django.utils import get_field_names_by_model
                        from .django.utils import get_field_type_in_py

                        related_fields = get_field_names_by_model(_meta_field.related_model)
                        _fields = _meta_field.related_model._meta.fields
                        _real_fk_field_name = _fields[related_fields.index(fk_field_name)].name
                        field_type_i = get_field_type_in_py(_meta_field.related_model, _real_fk_field_name)
                        _conved_flag = True
                    else:
                        if '__' in fk_field_name:
                            print(f'*** 警告: 仅支持一层外键自动化转换类型! 自动转换失败字段: `{serializer_field_i}`')

                if not _conved_flag:
                    field_type_i = convert_db_field_type_to_python_type(str(field_type_i).replace('()', ''))
                print(serializer_field_i, verbose_name_i, field_type_i)
                can_be_empty_i = True

                field_names.append(serializer_field_i)
                verbose_names.append(verbose_name_i)
                field_type_ls.append(field_type_i)
                can_be_empty_ls.append(can_be_empty_i)

            # --- 获取serializer_class
            serializer_class = v.serializer_class

            if issubclass(v, BaseListView):
                if serializer_class is None:
                    if v.list_serializer_class:
                        serializer_class = v.list_serializer_class
                    if v.retrieve_serializer_class:
                        # 有限详情页的序列化器
                        serializer_class = v.retrieve_serializer_class

            # --- 示例字段
            smeta = serializer_class.Meta
            if hasattr(smeta, 'fields'):
                sf = serializer_class.Meta.fields
                if ret_all_fields is True or sf == '__all__':
                    # sf = '__all__'
                    sf = serializer_class.Meta.fields = field_names
            else:
                sf = field_names.copy()
                exclude_ls = smeta.exclude
                if exclude_ls:
                    for e in exclude_ls:
                        sf.remove(e)

            try:
                # 直接调用view的get接口
                result = v.as_view()(request._request).data.get('result')

                if isinstance(result, dict):
                    dc_ls = result.get('data')
                elif isinstance(result, list):
                    dc_ls = result
                else:
                    raise TypeError(f'result为未知的返回类型! {type(result)}')
                dc_ls = dc_ls[:3]
                if not dc_ls:
                    raise ValueError('\n============== 返回的样例数据`example_data`为空! =============\n')

            except Exception as e:
                try:
                    print('--- Error! 调用view方法失败, 尝试使用model方案... ', e)
                    # --- 示例数据, 用model
                    qs_ls = md.objects.all()[:3]
                    # q0 = qs_ls[0]     # 单个数据
                    try:
                        dc_ls = serializer_class(qs_ls, many=True).data
                    except Exception as e:
                        print('--- Error! 序列化出错! 可能未携带annotate所需字段? 将自动生成基本序列化器! --- ' + str(e))
                        serializer_class = get_base_serializer(qs_ls)
                        dc_ls = serializer_class(qs_ls, many=True).data

                    dc_ls = [dict(dc) for dc in dc_ls]      # 返回数据示例
                except Exception as e:
                    print(f'========== 错误信息: view_class_name[{view_class_name}], view_class_instance[{v}]')
                    raise e

            # -- 简化过长的字段
            for dc in dc_ls:
                for k, v in dc.items():
                    if isinstance(v, str):
                        if len(v) > MAX_LEN:
                            dc[k] = v[:MAX_LEN] + '...略'
                print(dc)

            output_to_file_and_prt('---------- 示例数据')

            _ret_dc = self.ret_dc.copy()
            _ret_dc['result']['data'] = dc_ls

            # 整理`response`的格式
            response_render_format = {
                'status': 'status',
                'msg': 'msg',
                'result': 'result',
            }
            if hasattr(self, 'response_render_format') and getattr(self, 'response_render_format'):
                response_render_format = self.response_render_format
            res_context_dc['response_render_format'] = response_render_format

            for k, v in response_render_format.items():
                _ret_dc[v] = _ret_dc.pop(k)
            example_data = json.dumps(_ret_dc, sort_keys=False, indent=4, separators=(', ', ': '), ensure_ascii=False)

            output_to_file_and_prt(example_data)
            res_context_dc['example_data'] = str(example_data)  # context: 示例数据
            output_to_file_and_prt()

            # --- 参数说明
            print(field_names, verbose_names)

            # region # --- 分析属于那种请求类型`context_request_type`
            view_class_type = 'APIView'
            if hasattr(view_class_instance, '_name'):
                view_class_type = getattr(view_class_instance, '_name')

            post_type_ls = getattr(view_class_instance, 'post_type_ls') if hasattr(view_class_instance,
                                                                                   'post_type_ls') else None

            context_request_type = '其它'
            if view_class_type == 'BaseListView':
                context_request_type = '基本查找类'
            elif view_class_type == 'CompleteModelView':
                context_request_type = '增删查改类'
            elif view_class_type == 'AdvancedSearchView':
                context_request_type = '高级检索类'
            elif view_class_type == 'BaseFullTextSearchView':
                context_request_type = '全文检索类'
            res_context_dc['context_request_type'] = context_request_type
            res_context_dc['view_class_type'] = view_class_type
            res_context_dc['post_type_ls'] = post_type_ls
            # endregion

            filter_fields__doc = ""
            res_context_dc['has_filter_fields'] = False
            if filter_fields:
                filter_fields__doc = "| 类型 | 字段名 | 说明 | 必填 |\n| --- | --- | --- | --- |\n"
                res_context_dc['has_filter_fields'] = True

            if view_class_type == 'BaseFullTextSearchView':
                filter_fields__doc = "| 类型 | 字段名 | 说明 | 必填 |\n| --- | --- | --- | --- |\n"
                filter_fields__doc += "| str  | search_keywords   | 全文检索关键词   | 否 |\n"
                _p = 'use_relevant_id_param'
                if hasattr(view_class_instance, _p) and getattr(view_class_instance, _p):
                    filter_fields__doc += "| int | relevant_id   | 将要做相关推荐的对象id     | 否 |\n"

            if ADD_CAN_BE_EMPTY:
                ss = "| 类型 | 字段名 | 说明 | 必填 |\n| --- | --- | --- | --- |\n"
            else:
                ss = "| 类型 | 字段名 | 说明 |\n| --- | --- | --- |\n"

            for field_name, verbose_name, can_be_empty, field_type in zip(field_names, verbose_names, can_be_empty_ls, field_type_ls):
                print(field_name, verbose_name, can_be_empty)

                si = ''
                if sf == '__all__' or field_name in sf:
                    # field_type = get_field_type_in_py(md, field_name)
                    if ADD_CAN_BE_EMPTY:
                        must_fill = '否' if can_be_empty else '是'
                        si = f'| {field_type} | {field_name} | {verbose_name} | { must_fill } |\n'
                    else:
                        si = f'| {field_type} | {field_name} | {verbose_name} |\n'
                ss += si

                if filter_fields and (filter_fields == '__all__' or field_name in filter_fields):
                    filter_fields__doc += f'| {field_type} | {field_name} | {verbose_name} | 否 |\n'

            output_to_file_and_prt('---------- 参数说明')
            parameters_explain = ss
            output_to_file_and_prt(parameters_explain)
            res_context_dc['parameters_explain'] = str(parameters_explain)  # context: 参数说明

            res_context_dc['filter_fields__doc'] = str(filter_fields__doc)  # filter_fields__doc: 过滤字段

            output_to_file_and_prt()

            print(parameters_explain)

            # if convert_query_parameter_to_bool(open_output_txt_file):
            if convert_query_parameter_to_bool(path_of_jinja2_template):
                # abs_path = os.path.join(settings.BASE_DIR, 'authors/myTestTemplates.html')
                # path_of_jinja2_template = path_of_jinja2_template if os.path.exists(path_of_jinja2_template) else os.path.exists(os.path.join(settings.BASE_DIR, path_of_jinja2_template))
                path_of_jinja2_template = os.path.join(settings.BASE_DIR, path_of_jinja2_template)
                if sys.platform == 'win32':
                    path_of_jinja2_template = path_of_jinja2_template.replace('/', '\\')
                else:
                    path_of_jinja2_template = path_of_jinja2_template.replace('\\', '/')

                my_api_assert_function(os.path.exists(path_of_jinja2_template), f'path_of_jinja2_template路径不存在![{path_of_jinja2_template}]')
                print('--- res_context_dc:', res_context_dc)

                # region # --- 解析`introduction`, 获取[标题, 简要描述, 请求url]等字段
                introduction = res_context_dc.get('introduction')
                if introduction:
                    # --- 获取标题`introduction_title`
                    reg = re.compile(r'^\n(.+?)\n')
                    match = reg.search(introduction)
                    if match:
                        introduction_title = match.group(1).strip()
                        introduction_title = re.sub(r'^#+ +', '', introduction_title)   # 去掉开头的`#`
                        res_context_dc['introduction_title'] = introduction_title

                    # --- 获取示例url`introduction_url`
                    reg = re.compile(r'.*?/.+/.+/.*')
                    match = reg.findall(introduction)
                    if match:
                        _introduction_url = []
                        for m_i in match:
                            m_i = m_i.strip()
                            if 'POST' in m_i:
                                reg = re.compile(m_i + '.*?' + r'\n.*(\{.*?\})[ \t]*\n', re.S)      # 只能匹配POST后的一个大括号!
                                # m = reg.search(introduction)
                                # if m:
                                #     text = m.group(1)
                                #     reg = re.compile('^.*(\{.*?\})\n', re.S)
                                #     _m = reg.search(text)
                                #     _m and print(_m.group(1))
                                #     dc = json.dumps(json.loads(_m.group(1)), sort_keys=False, indent=4, separators=(', ', ': '), ensure_ascii=False)
                                findall_ls = reg.findall(introduction)
                                # print(findall_ls)
                                if findall_ls:
                                    findall_i = findall_ls[0]
                                    try:
                                        findall_str = json.dumps(json.loads(findall_i), sort_keys=False, indent=4, separators=(', ', ': '), ensure_ascii=False)
                                    except Exception as e:
                                        e_str = '****** POST请求携带的字典错误!' + str(e)
                                        from warnings import warn
                                        warn(e_str)
                                        # raise ValueError(e_str)
                                    m_i += '\n' + findall_str
                            _introduction_url.append(m_i)
                        introduction_url = '\n'.join(_introduction_url)
                        res_context_dc['introduction_url'] = introduction_url

                    reg = re.compile(r'\n( *?- .+)')
                    match = reg.findall(introduction)
                    # from bddjango import show_ls
                    # show_ls(match)
                    if match:
                        _introduction_summary = []
                        blank_ls = []
                        for summary_i in match:
                            summary_i: str
                            m1 = re.match(r'^ *', summary_i)
                            blank_i = m1.span()[-1] if m1 else 0
                            blank_ls.append(blank_i)
                            _introduction_summary.append(summary_i)
                        blank_min = min(blank_ls)       # 将所有简介缩进到最左侧, 不然会变成代码块!
                        _introduction_summary = [s_i[blank_min:] for s_i in _introduction_summary]
                        introduction_summary = '\n'.join(_introduction_summary)
                    else:
                        introduction_summary = '- ' + introduction_title
                    res_context_dc['introduction_summary'] = introduction_summary
                # endregion

                # region # --- 开始填充jinja模板
                with open(path_of_jinja2_template, encoding='utf-8') as file_:
                    template = Template(file_.read())

                # from jinja2 import PackageLoader, Environment, FileSystemLoader
                # env = Environment(loader=PackageLoader('python_project', 'templates'))  # 创建一个包加载器对象

                # env = Environment(loader=FileSystemLoader(app_name))  # 文件加载器, 可用`list_templates`方法查看存在哪些东西
                # os.path.exists(path_of_jinja2_template)
                # template = env.get_template(path_of_jinja2_template)
                content = template.render(**res_context_dc)
                with open(output_fname, 'w', encoding='utf-8') as f:
                    f.write(content)
                # endregion

            # 获取output文件, 仅能获取一个view_class
            get_output_file = convert_query_parameter_to_bool(request_data.get('get_output_file'))
            if get_output_file:
                newFileName = output_fname
                with open(output_fname, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/txt')
                    response['Content-Disposition'] = 'attachment; filename="{}"'.format(newFileName)
                    response["Access-Control-Allow-Origin"] = '*'
                    response["Server"] = '*'
                    return response
            else:
                open_output_txt_file = request_data.get('open_output_txt_file', self.open_output_txt_file)
                if sys.platform in ['win32', 'darwin'] and convert_query_parameter_to_bool(open_output_txt_file):
                    for i in range(5):
                        tt.sleep(1)
                        print('111')
                        if os.path.exists(output_fname):
                            print('222')
                            if sys.platform == 'win32':
                                os.startfile(output_fname)
                            elif sys.platform == 'darwin':
                                os.system(f'open {output_fname}')
                            else:
                                my_api_assert_function(f'系统类型错误? sys.platform: {sys.platform}')
                            tt.sleep(SLEEP_TIME)
                            # tt.sleep(10)
                            # os.remove(output_fname)
                            from bddjango.adminclass import remove_temp_file
                            remove_temp_file('tempdir', MAX_TEMPS=10)
                            break
                else:
                    print('--- output_fname: ', output_fname)
                    with open(output_fname, 'r', encoding='utf-8') as f:
                        # print(f.read())

                        res_context_dc.update(
                            {
                                'output_fname': output_fname,
                                'output_content': f.read(),
                            }
                        )
            ret_dc = {
                'res_context_dc': res_context_dc
            }
            ret.append(ret_dc)

        # endregion

        # output_file.close()
        return APIResponse(ret, 200, 'ok')






