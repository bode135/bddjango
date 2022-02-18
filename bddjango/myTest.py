from django.shortcuts import render
from . import models, serializers
from rest_framework.views import APIView
from django.core.cache import cache
from rest_framework.request import Request
import sys

from bddjango.django import APIResponse, BaseListView, api_decorator
from bddjango.MultipleConditionSearch import AdvancedSearchView
from bddjango import convert_db_field_type_to_python_type
from bddjango import convert_query_parameter_to_bool
from bdtime import tt

global tmp


class MyTest(APIView):
    """
    自动生成wiki文档

    - app_name: 目标app, 必填
    - view_class_name: 目标view, 可空
    - ret_all_fields: 是否返回全部字段, 默认False
    - ADD_CAN_BE_EMPTY: 增加“能否为空”字段, 默认False



    {#[*]( "这是注释")#}

    {#[ ]( "最好写上 [GET POST] 等")#}
    """

    open_output_txt_file = True  # `win`在运行完成后, 打开输出的`txt`文件
    path_of_jinja2_template = 'myTestTemplates.html'  # 使用`jinja2`模板来生成`wiki`模板

    def get(self, request, *args, **kwargs):
        """自动生成wiki文档"""
        res_context_dc = {}  # 将结果变量储存为文本字典, 好用`jinja2`来填写模板

        ret = []
        request_data = request.GET

        # --- 必填
        app_name = request_data.get('app_name')
        assert app_name, 'app_name不能为空!'

        # --- 选填
        view_class_name = request_data.getlist('view_class_name')  # 可空
        ret_all_fields = request_data.getlist('ret_all_fields', False)  # 返回全部字段 or 只保留serializer_fields中返回的字段
        ADD_CAN_BE_EMPTY = request_data.getlist('ADD_CAN_BE_EMPTY', False)  # 增加“能否为空”字段
        SLEEP_TIME = request_data.get('SLEEP_TIME', 0.2)  # sleep时间, 也就是文件保存到打开的间隔
        MAX_LEN = request_data.get('MAX_LEN', 100)  # 示例数据最长字段限制

        exec(f'global tmp; from {app_name} import views as tmp;')  # 执行
        print('---------', tmp)

        views = tmp
        func_ls = dir(views)

        s = 0
        vs = []
        for f in func_ls:
            md = getattr(views, f)
            if hasattr(md, 'queryset') and hasattr(md, 'serializer_class'):
                print('---------', f, md)
                if getattr(md, 'queryset') is not None and (
                        getattr(md, 'serializer_class') or getattr(md, 'list_serializer_class') or getattr(md,
                                                                                                           'auto_generate_serializer_class') or getattr(
                        md, 'retrieve_serializer_class')):
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
        if 1:
            """生成一个view的wiki文档"""
            from bddjango.django import get_base_model
            from django.forms import model_to_dict
            from bddjango import show_json
            from bddjango.django import get_field_type_in_py
            from bddjango import create_dir_if_not_exist, create_file_if_not_exist
            import re
            import json
            import os

            tempdir_rootpath = 'tempdir'  # 临时输出文件的根目录
            output_dirpath = os.path.join(tempdir_rootpath, 'output')  # 临时输出文件的子目录
            create_dir_if_not_exist(tempdir_rootpath)
            create_dir_if_not_exist(output_dirpath)

            path_of_jinja2_template = request_data.get('path_of_jinja2_template', self.path_of_jinja2_template)

            for view_id in range(len(vs)):
                # view_id = 0       # debug
                # issubclass(v, BaseListView)

                # --- 获取单个view的名称和实例
                fv = vs[view_id]
                f, v = fv  # view_class_name, view_class_instance

                # --- 输出文件的路径
                output_f_suffix = '.txt'  # 使用`.md`打开太慢, `typora`会报错
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
                res_context_dc['introduction'] = v.__doc__  # context: 简介
                output_to_file_and_prt(res_context_dc['introduction'])

                output_to_file_and_prt('****************')
                output_to_file_and_prt()

                output_to_file_and_prt(f'\n=======  {view_id}  =========  \n')
                res_context_dc['view_id'] = str(view_id)  # context: view_id

                view_class_name, view_class_instance = f, v
                output_to_file_and_prt(
                    f'---, view_class_name: [{view_class_name}], view_class_instance: [{view_class_instance}]')
                res_context_dc['view_class_name'] = str(view_class_name)  # context: view_class_name
                res_context_dc['view_class_instance'] = str(view_class_instance)  # context: view_class_instance

                output_to_file_and_prt()

                # --- 获取model和meta
                md = get_base_model(v.queryset)
                meta = md._meta

                url = f'/api/{meta.app_label}/{f}/'

                output_to_file_and_prt('------------ 请求URL')
                output_to_file_and_prt(f"`{url}`")
                res_context_dc['request_url'] = str(url)  # context: 请求URL

                output_to_file_and_prt()

                if hasattr(v, 'filter_fields'):
                    if v.filter_fields:
                        output_to_file_and_prt('------------ 过滤字段')
                        output_to_file_and_prt(f"`{v.filter_fields}`")
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

                if v.auto_generate_serializer_class:
                    from bddjango import get_base_serializer
                    v: BaseListView
                    v__serializer_class = v().get_serializer_class()
                    v__queryset = get_base_model(v().get_queryset()).objects.all()
                    v__serializer_class(v__queryset, many=True).data
                    v__serializer_class.__dict__.get('_declared_fields')
                    v.serializer_class = v__serializer_class

                # --- 把serializers里面的拓展字段加进field_names
                serializer_field_ls = v.serializer_class.__dict__.get('_declared_fields')
                text = v.serializer_class.__doc__ or ""

                for serializer_field_i, field_type_i in serializer_field_ls.items():
                    reg = re.compile(f'^.*{serializer_field_i}: +(.*?) *$', re.M)
                    match = reg.search(text)
                    if match:
                        verbose_name_i = match.group(1)
                    else:
                        verbose_name_i = serializer_field_i

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

                if 0:
                    # 这里尝试用drf的测试方法去获取返回示例数据
                    from rest_framework.test import APIRequestFactory
                    view = v.as_view()
                    print(view)
                    v_str = str(v)
                    example_url = v.__doc__

                    reg = re.compile(r"\.(\w+)\'>$")
                    match = reg.search(v_str)
                    v_name = match.group(1)
                    v_url = f'api/{app_name}/{v_name}'
                    # 找到url, 然后用测试模块测试
                    factory = APIRequestFactory()
                    rq = factory.get(v_url)
                    v.as_view()(rq).data
                    1

                    from flow_statistics.utils import get_statistics_result
                    get_statistics_result(v.queryset, get_serializer_data=False)
                    print('---', v.as_view()(request._request, *args, **kwargs).data)
                    v().get_list_ret(request._request, *args, **kwargs)

                    # v(request._request).as_view().get_queryset()
                    v.as_view()(request._request, *args, **kwargs).data

                    v.as_view()(request._request, *args, **kwargs)
                    v.as_view()(request._request, *args, **kwargs).data

                    v.as_view()
                    v(request).get_queryset()
                    type(v)
                    from flow_statistics.views import Statistics
                    get_statistics_result(v.queryset, get_serializer_data=False)

                    type(Statistics)
                    Statistics.get_queryset(Statistics)

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

                except Exception as e:
                    print('--- Error! 调用view方法失败, 尝试使用model方案... ', e)
                    # --- 示例数据, 用model
                    qs_ls = md.objects.all()[:3]
                    # q0 = qs_ls[0]     # 单个数据
                    dc_ls = serializer_class(qs_ls, many=True).data
                    dc_ls = [dict(dc) for dc in dc_ls]  # 返回数据示例

                # -- 简化过长的字段
                for dc in dc_ls:
                    for k, v in dc.items():
                        if isinstance(v, str):
                            if len(v) > MAX_LEN:
                                dc[k] = v[:MAX_LEN] + '...略'
                    print(dc)

                output_to_file_and_prt('---------- 示例数据')
                example_data = json.dumps(dc_ls, sort_keys=False, indent=4, separators=(', ', ': '), ensure_ascii=False)
                output_to_file_and_prt(example_data)
                res_context_dc['example_data'] = str(example_data)  # context: 示例数据
                output_to_file_and_prt()

                # --- 参数说明
                print(field_names, verbose_names)

                if ADD_CAN_BE_EMPTY:
                    ss = "| 类型 | 字段名 | 说明 | 能否为空 |\n| --- | --- | --- | --- |\n"
                else:
                    ss = "| 类型 | 字段名 | 说明 |\n| --- | --- | --- |\n"

                for field_name, verbose_name, can_be_empty, field_type in zip(field_names, verbose_names,
                                                                              can_be_empty_ls, field_type_ls):
                    print(field_name, verbose_name, can_be_empty)

                    si = ''
                    if sf == '__all__' or field_name in sf:
                        # field_type = get_field_type_in_py(md, field_name)
                        if ADD_CAN_BE_EMPTY:
                            si = f'| {field_type} | {field_name} | {verbose_name} | {can_be_empty} |\n'
                        else:
                            si = f'| {field_type} | {field_name} | {verbose_name} |\n'
                    ss += si

                output_to_file_and_prt('---------- 参数说明')
                parameters_explain = ss
                output_to_file_and_prt(parameters_explain)
                res_context_dc['parameters_explain'] = str(parameters_explain)  # context: 参数说明
                output_to_file_and_prt()

                open_output_txt_file = request_data.get('open_output_txt_file', self.open_output_txt_file)

                if convert_query_parameter_to_bool(open_output_txt_file):
                    if convert_query_parameter_to_bool(path_of_jinja2_template):
                        """
                        解析introduction

                        `
                        标题
                        - 这一定是简介, 没有的话, 简介就是标题

                        /api/authors/InstitutionType/   # 接口, 可能会在最前方指明请求类型[GET, POST]
                        `

                        """
                        print('--- res_context_dc:', res_context_dc)

                        # region # --- 解析`introduction`, 获取[标题, 简要描述, 请求url]等字段
                        introduction = res_context_dc.get('introduction')
                        if introduction:

                            # --- 获取标题`introduction_title`
                            reg = re.compile(r'^\n(.+?)\n')
                            match = reg.search(introduction)
                            if match:
                                introduction_title = match.group(1).strip()
                                res_context_dc['introduction_title'] = introduction_title

                            # --- 获取示例url`introduction_url`
                            reg = re.compile(r'.*?/.+/.+/.*')
                            match = reg.findall(introduction)
                            if match:
                                _introduction_url = []
                                for m_i in match:
                                    m_i = m_i.strip()
                                    _introduction_url.append(m_i)
                                introduction_url = '\n'.join(_introduction_url)
                                res_context_dc['introduction_url'] = introduction_url

                            reg = re.compile(r'\n( *?- .+)')
                            match = reg.findall(introduction)
                            from bddjango import show_ls
                            show_ls(match)
                            if match:
                                _introduction_summary = []
                                for summary_i in match:
                                    _introduction_summary.append(summary_i)
                                introduction_summary = '\n'.join(_introduction_summary)
                            else:
                                introduction_summary = '- ' + introduction_title
                            res_context_dc['introduction_summary'] = introduction_summary
                        # endregion

                        # region # --- 分析属于那种请求类型`context_request_type`
                        view_class_type = 'APIView'
                        if hasattr(view_class_instance, '_name'):
                            view_class_type = getattr(view_class_instance, '_name')

                        context_request_type = '其它'
                        if view_class_type == 'BaseListView':
                            context_request_type = '基本查找类'
                        elif view_class_type == 'CompleteModelView':
                            context_request_type = '增删查改类'
                        elif view_class_type == 'AdvancedSearchView':
                            context_request_type = '高级检索类'
                        res_context_dc['context_request_type'] = context_request_type
                        # endregion

                        # region # --- 开始填充jinja模板
                        from jinja2 import PackageLoader, Environment, FileSystemLoader
                        # env = Environment(loader=PackageLoader('python_project', 'templates'))  # 创建一个包加载器对象
                        env = Environment(loader=FileSystemLoader(app_name))  # 文件加载器, 可用`list_templates`方法查看存在哪些东西
                        template = env.get_template(path_of_jinja2_template)
                        content = template.render(**res_context_dc)
                        with open(output_fname, 'w') as f:
                            f.write(content)
                        # endregion

                    if sys.platform == 'win32':
                        os.startfile(output_fname)
                        tt.sleep(SLEEP_TIME)
                        os.remove(output_fname)
                    else:
                        print('--- output_fname: ', output_fname)
                        with open(output_fname, 'r') as f:
                            print(f.read())

                            ret.append({output_fname: f.read()})

        ret_dc = {
            'res_context_dc': res_context_dc
        }
        ret.append(ret_dc)

        # output_file.close()
        return APIResponse(ret, 200, 'ok')
