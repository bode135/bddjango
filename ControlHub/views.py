from rest_framework.views import APIView
from bddjango import APIResponse


# region # --- admin首页的echarts图表
from django.shortcuts import render
from rest_framework.views import View
from rest_framework.response import Response
import json
from bddjango import conv_queryset_to_dc_ls


def sort_dc_ls1_by_ls2(dc_ls1, key, ls2=None, reverse=False):
    """
    将dc_ls1按key字段排序, 排序顺序可以指定为ls2.
    """
    if ls2 is not None:
        res = [i for j in ls2 for i in dc_ls1 if i.get(key) == j]  # show_ls(info_dc_ls)
        if reverse:
            res.reverse()
    else:
        res = sorted(dc_ls1, key=lambda k: k[key], reverse=reverse)
    return res


class HomeChartView(View):
    def get(self, request, *args, **kwargs):
        from bddjango import get_model_verbose_name_dc
        from django.contrib.contenttypes.models import ContentType
        from django.forms import model_to_dict
        from bddjango import get_base_model, get_base_queryset
        from django.db.models import Q
        from django.db import models as m
        from index import models

        # bar表要统计的模型
        ct_qs_ls = ContentType.objects.filter(
            app_label='index'
        ).order_by('model').exclude(model='LogLawRecommend'.lower())
        # model_to_dict(ct_qs_ls.last())

        # 饼状图要统计的模型和字段
        statistic_model = models.WenWuShuJuBiao
        field_name = 'lei_bie'
        # statistic_model = models.RenWuShuJuBiao
        # field_name = 'shou_zi_mu'

        model_verbose_name_dc = get_model_verbose_name_dc()
        model_verbose_name_dc = {v: k for k, v in model_verbose_name_dc.items()}

        info_dc_ls = []
        # xAxis__data = []
        for ct_qs_i in ct_qs_ls:
            # break
            _app_label = ct_qs_i.app_label
            model_name = ct_qs_i.model
            verbose_name = model_verbose_name_dc.get(ct_qs_i)
            try:
                count = get_base_queryset(ct_qs_i).count()
            except Exception as e:
                print(f'--- HomeChartView.get_base_queryset(ct_qs_i).count(): 获取{ct_qs_i}失败! error: {e}')
                continue
            info_dc_i = {
                'model_name': model_name,
                'name': verbose_name,
                'value': count,
                'url': f'/api/admin/{_app_label}/{model_name}/',
            }
            info_dc_ls.append(info_dc_i)
            # xAxis__data.append(verbose_name)

        # 可以在这里指定x轴标签的顺序
        # xAxis__data = ordering_ls = ['图书表', '图表基本表', '章节表', '章节_人物表', '章节_机构表', '章节_地点表', '章节_事件表']
        # xAxis__data = ordering_ls = ['评论树表', 'comment']
        ordering_ls = None
        # ordering_ls = ['问题表', '相关案例表']      # , '测试表'
        # ordering_field = 'name'

        if ordering_ls:
            info_dc_ls = sort_dc_ls1_by_ls2(info_dc_ls, 'name', ls2=ordering_ls)
        else:
            info_dc_ls = sort_dc_ls1_by_ls2(info_dc_ls, 'value', reverse=True)

        xAxis__data = [dc.get('name') for dc in info_dc_ls]

        # region 自动设置bar_type的值, 大于10倍差距则用log
        value_ls = [dc.get('value') for dc in info_dc_ls]

        bar_type = 'value'
        if value_ls:
            value_max = max(value_ls)
            value_min = min(value_ls)
            if value_min and value_max / value_min >= 10:
                bar_type = 'log'
        # endregion

        # bar_type = 'value'
        # 转为json格式
        title__text = '各表数据量对比'
        info_js = json.dumps(info_dc_ls)
        xAxis__data = json.dumps(xAxis__data)
        legend__data = json.dumps(['数量'])

        # --- 饼状图
        base_url = f'/api/admin/{statistic_model._meta.app_label}/{statistic_model._meta.model_name}/?{field_name}'
        ordering = ['-counts']

        chart_base_count = statistic_model.objects.count()
        field_qsv = statistic_model.objects.values(field_name)
        statistic_qsv_ls = field_qsv.annotate(counts=m.Count('pk')).order_by(*ordering)
        statistic_dc_ls = conv_queryset_to_dc_ls(statistic_qsv_ls)
        # show_ls(statistic_dc_ls)

        # --- 把"其他"放到最后
        LAST_VALUE = None
        k = -1
        for i in range(len(statistic_dc_ls)):
            dc_i = statistic_dc_ls[i]
            # break
            v = dc_i.get(field_name)
            if v == LAST_VALUE:
                k = i

            value = dc_i.get('counts')
            dc_i['value'] = value
            dc_i['percent'] = "{}%".format(value*10000//chart_base_count/100)        # 保留2位有效数字, 向下取整
            dc_i['name'] = dc_i.get(field_name)
            dc_i['url'] = base_url + f"=" + v if v else base_url + f'__isnull=1'

        if statistic_dc_ls:
            statistic_dc_ls.append(statistic_dc_ls.pop(k))

        # num = 5     # 最多返回多少个
        # else_dc = statistic_dc_ls.pop(k)
        # statistic_dc_ls = statistic_dc_ls[:num] + [else_dc]

        pie_dc = {
            'title': f'[{statistic_model._meta.verbose_name} - {getattr(statistic_model, field_name).field.verbose_name.upper()}]类型统计',
            'series': {
                'name': '数量',
                'data': statistic_dc_ls,
            }
        }
        pie_dc = json.dumps(pie_dc)

        context = {
            'info_js': info_js,
            'bar_type': bar_type,
            'xAxis__data': xAxis__data,
            'legend__data': legend__data,
            'show__legend': False,
            # 'legend__data': [],
            'title__text': title__text,
            'pie_dc': pie_dc,
        }
        return render(request, "admin/home_charts.html", context=context)
# endregions


class Test(APIView):
    """
    测试是否运行成功
    """

    def get(self, request):
        return APIResponse()




