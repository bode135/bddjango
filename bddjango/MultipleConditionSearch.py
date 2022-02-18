"""
高级检索
"""

from .django import BaseListView, APIResponse
from django.db.models import Q
from django.db.models import QuerySet
import json
from .django import get_base_model, get_base_queryset


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

        # print('~~~~~~~~~___', self.model)
        # if isinstance(self.model, QuerySet):
        #     assert self.model.count(), '请指定检索的queryset类型!'
        #     model = self.model[0]
        # else:
        #     model = self.model

        # print(accuracy)
        # if hasattr(model, '_meta'):
        #     if model._meta.get_field(search_field).get_internal_type() in ('TextField', 'CharField'):
        #         if accuracy:
        #             cmd = f'self.qs = Q({search_field}="{search_keywords}")'
        #         else:
        #             cmd = f'self.qs = Q({search_field}__contains="{search_keywords}")'
        #     else:
        #         cmd = f'self.qs = Q({search_field}={search_keywords})'
        # else:
        #     if accuracy:
        #         cmd = f'self.qs = Q({search_field}="{search_keywords}")'
        #     else:
        #         cmd = f'self.qs = Q({search_field}__contains="{search_keywords}")'

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

        self.queryset = []
        self.condition_ls = condition_ls        # 检索条件
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


class AddQ:
    """
    根据前端的Q_add_ls参数, 生成QS, 用以查询结果.

    - 样例数据:
     "Q_add_ls": [
        {
            "add_logic": "and",
            "Q_ls": [
                {
                    "add_logic": "and",
                    "search_field": "title",
                    "search_keywords": "中国",
                    "accuracy": "0"
                },
                {
                    "add_logic": "or",
                    "search_field": "title",
                    "search_keywords": "百年",
                    "accuracy": "0"
                }
            ]
        },
        {
            "add_logic": "and",
            "Q_ls": [
                {
                "add_logic": "and",
                "search_field": "publication_date",
                "search_keywords": "2020-01-01",
                "accuracy": "gte"
                },
                {
                    "add_logic": "and",
                    "search_field": "publication_date",
                    "search_keywords": "2021-01-01",
                    "accuracy": "lte"
                }
            ]
        }
    ]
    """

    def __init__(self, Q_add_ls):
        self.Q_add_ls = Q_add_ls
        self.QS = Q()

    def _get_QS_i(self, Q_add_i):
        """
        将Q_add_ls拆分为Q_ls后, 获得对应的qs
        """
        mcs = MultipleConditionSearch('', condition_ls=Q_add_i)
        qs = mcs.add_multiple_conditions()
        return qs

    def get_QS(self):

        for Q_add_i in self.Q_add_ls:
            add_logic = Q_add_i.get('add_logic')
            qs_ls = Q_add_i.get('Q_ls')
            qs = self._get_QS_i(qs_ls)

            if add_logic == 'and':
                self.QS.add(qs, Q.AND)
            elif add_logic == 'or':
                self.QS.add(qs, Q.OR)
            elif add_logic == 'not':
                self.QS.add(~qs, Q.AND)
            else:
                raise ValueError(f'add_logic must choice in [and, or, not]!')

        return self.QS


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
    _name = 'AdvancedSearchView'
    
    queryset = None
    serializer_class = None
    search_condition_ls = None

    def post(self, request, *args, **kwargs):
        self._post_type = post_type = 'list'
        ret, status, msg = self.get_list_ret(request, *args, **kwargs)
        return APIResponse(ret, status=status, msg=msg)

    def get_queryset(self):
        query_dc = self.get_request_data()
        Q_add_ls = query_dc.get('Q_add_ls')
        if Q_add_ls:
            original_qs_ls = get_base_queryset(super().get_queryset())
            add_q = AddQ(Q_add_ls=Q_add_ls)
            qs = add_q.get_QS()
            self.queryset = original_qs_ls.filter(qs)
            return self.queryset

        search_condition_ls = query_dc.get('search_condition_ls', [])
        if search_condition_ls:
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




