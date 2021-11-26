"""
高级检索
"""

from .django import BaseListView, APIResponse
from django.db.models import Q
from django.db.models import QuerySet
import json


class SingleConditionSearch:
    """
    # 单一条件检索

    - 示例:
    condition = {
        "add_logic": "and",
        "search_field": "academy",
        "search_keywords": "人文艺术",
        "accuracy": "0"
    }
    """
    model = None
    serializer = None
    qs = Q()

    def __init__(self, condition: dict):
        self.condition = condition
        self.search_type, self.search_field, self.search_keywords = condition.get(
            'add_logic'), condition.get(
            'search_field'), condition.get('search_keywords')
        self.accuracy = condition.get('accuracy', 0)
        self.qs = Q()
        self.queryset = None

    def add_field_as_accuracy(self):
        """
        根据accuracy的值, 增加field_name

        :param search_field: 字段名
        :param search_keywords: 字段值
        :param accuracy: 精确检索 or 模糊检索
        :return: qs
        """
        search_field, search_keywords, accuracy = self.search_field, self.search_keywords, self.accuracy

        assert self.model is not None, '请指定model类型!'

        if isinstance(self.model, QuerySet):
            assert self.model.count(), '请指定检索的queryset类型!'
            model = self.model[0]
        else:
            model = self.model

        print(accuracy)
        if hasattr(model, '_meta'):
            if model._meta.get_field(search_field).get_internal_type() in ('TextField', 'CharField'):
                if accuracy:
                    cmd = f'self.qs = Q({search_field}="{search_keywords}")'
                else:
                    cmd = f'self.qs = Q({search_field}__contains="{search_keywords}")'
            else:
                cmd = f'self.qs = Q({search_field}={search_keywords})'
        else:
            if accuracy:
                cmd = f'self.qs = Q({search_field}="{search_keywords}")'
            else:
                cmd = f'self.qs = Q({search_field}__contains="{search_keywords}")'

        def get_suffix_by_accuracy(accuracy):
            """
            根据accuracy的取值, 获得suffix

            * Q({search_field}__{suffix}="{search_keywords}")
            """
            try:
                # 尝试将accuracy转换为int, 代表[精确/模糊]匹配
                if isinstance(accuracy, str) and len(accuracy) == 1:
                    suffix = int(accuracy)
                else:
                    suffix = accuracy

                # 将suffix转义
                if isinstance(suffix, int):
                    if suffix:
                        suffix = ''
                    else:
                        suffix = 'contains'
                else:
                    suffix = accuracy
            except:
                suffix = accuracy
            return suffix

        suffix = get_suffix_by_accuracy(accuracy)
        if suffix:
            cmd = f'self.qs = Q({search_field}__{suffix}="{search_keywords}")'
        else:
            cmd = f'self.qs = Q({search_field}="{search_keywords}")'

        # print(search_field, search_keywords, accuracy, '---', self.qs)
        exec(cmd)

        qs = self.qs
        return qs

    def get_q(self):
        """
        重点
        :return: 单个条件的检索逻辑
        """
        qs = self.add_field_as_accuracy()
        return qs


class MultipleConditionSearch:
    """
    # 多重条件检索(高级检索)

    - 示例:
    ```python
    search_condition_ls = [
            {
                "add_logic": "and",
                "search_field": "academy",
                "search_keywords": "人文艺术",
                "accuracy": "0"
            },
            {
                "add_logic": "and",
                "search_field": "name",
                "search_keywords": "博",
                "accuracy": "0"
            }
        ]

    mcs = MultipleConditionSearch(MySingleConditionSearch, search_condition_ls)
    mcs.add_multiple_conditions()
    mcs.QS
    queryset = mcs.get_queryset()
    ```

    """

    def __init__(self, model, condition_ls: list):
        self.QS = Q()
        # self.QS.add(Q(), Q.AND)

        self.queryset = []
        self.condition_ls = condition_ls        # 检索条件
        # if isinstance(model, QuerySet):
        #     assert model.count(), '请指定检索的queryset类型!'
        #     self.model = model[0]
        # else:
        self.model = model

        class MySingleConditionSearch(SingleConditionSearch):
            model = self.model

        self.SingleConditionSearch = MySingleConditionSearch      # 检索类型
        assert MySingleConditionSearch.model is not None, '请指定SingleConditionSearch的model类型!'

    def add_q(self, q, add_type: str):
        return MultipleConditionSearch.qs_add(self.QS, q, add_type)

    @staticmethod
    def qs_add(qs, q, add_type: str):
        """
        高级检索的条件拼接
        """
        if add_type == 'not':
            qs.add(~q, Q.AND)
        elif add_type == 'and':
            qs.add(q, Q.AND)
        elif add_type == 'or':
            qs.add(q, Q.OR)
        else:
            raise ValueError('qs_add: add_logic取值错误! add_logic must choice in [and, or, not]!')

        return qs

    def add_single_condition(self, condition: dict):
        """
        按单一条件补充QS
        """
        scs = self.SingleConditionSearch(condition)
        q = scs.get_q()
        return self.add_q(q, scs.search_type)

    def add_multiple_conditions(self):
        """
        按条件列表补充QS
        """
        condition_ls = self.condition_ls
        if not condition_ls or isinstance(condition_ls[0], list):
            return self.QS

        for condition in condition_ls:
            # print('检索前:', self.QS, '******', condition)
            self.add_single_condition(condition)

        return self.QS

    def get_queryset(self):
        if isinstance(self.model, QuerySet):
            self.queryset = self.model.filter(self.QS)
        else:
            self.queryset = self.model.objects.filter(self.QS)
        return self.queryset


class AdvancedSearchView(BaseListView):
    """
    高级检索

    POST /api/index/AdvancedSearch
    search_condition_ls = [
            {
                "add_logic": "and",
                "search_field": "prize_level",
                "search_keywords": 1,
                "accuracy": "0"
            },
            {
                "add_logic": "and",
                "search_field": "name",
                "search_keywords": "博得",
                "accuracy": "0"
            }
        ]
    """
    queryset = None
    serializer_class = None
    search_condition_ls = None

    def post(self, request, *args, **kwargs):
        ret, status, msg = self.get_list_ret(request, *args, **kwargs)
        return APIResponse(ret, status=status, msg=msg)

    def get_queryset(self):

        if self.search_condition_ls is None:
            search_condition_ls = self.request.data.get('search_condition_ls', [])
            if not search_condition_ls:
                search_condition_ls = self.request.query_params.get('search_condition_ls', [])
                if isinstance(search_condition_ls, str):
                    search_condition_ls = json.loads(search_condition_ls)
        else:
            search_condition_ls = self.search_condition_ls

        if search_condition_ls:
            mcs = MultipleConditionSearch(self.queryset, search_condition_ls)
            mcs.add_multiple_conditions()
            self.queryset = mcs.get_queryset()
        else:
            self.queryset = super().get_queryset()

        return self.queryset


