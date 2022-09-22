"""
高级检索
"""

from .django import BaseListView, APIResponse
from django.db.models import Q
from django.db.models import QuerySet
import json
from .django import get_base_model, get_base_queryset
from .django import my_api_assert_function
from .django import conv_to_queryset


def is_leaf(Q_ls):
    """
    判断`Q_ls`是否为叶子节点
    """
    if isinstance(Q_ls, dict):
        Q_ls = Q_ls.get('Q_ls')

    ret = True

    if Q_ls is None:
        return ret

    for Q_i in Q_ls:
        if 'Q_ls' in Q_i:
            ret = False
    return ret


def add_qs(QS, qs, add_logic):
    if add_logic == 'and':
        QS.add(qs, Q.AND)
    elif add_logic == 'or':
        QS.add(qs, Q.OR)
    elif add_logic == 'not':
        QS.add(~qs, Q.AND)
    else:
        raise ValueError(f'add_logic must choice in [and, or, not]!')
    return QS


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
            cmd = f'self.qs = Q({search_field}__{suffix}="{search_keywords}")'  # isnull时应转为bool! 待完善.
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
        self.condition_ls = condition_ls  # 检索条件
        self.model = model

        class MySingleConditionSearch(SingleConditionSearch):
            model = self.model

        self.SingleConditionSearch = MySingleConditionSearch  # 检索类型
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
            if condition.get('Q_ls'):
                print('这个是复合条件, 还不能处理 --- ', condition)
                continue
                # mcs = MultipleConditionSearch(self.queryset, condition)
                # mcs.add_multiple_conditions()

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

    debug = False

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

    def _QS_add_leaf_Q_i(self, QS, Q_i):
        add_logic = Q_i.get('add_logic')
        qs_ls = Q_i.get('Q_ls')
        qs = self._get_QS_i(qs_ls)
        QS = add_qs(QS, qs, add_logic)
        return QS

    def log(self, msg):
        if self.debug:
            print(msg)

    def _recursive_get_QS(self, Q_ls, QS=None, node_name=None):
        QS = Q() if QS is None else QS

        if node_name is None:
            self.log('\n\n=============================\n')

        self.log(f'*** 正在处理 node_name: [{node_name}] ***')

        for Q_i in Q_ls:
            _node_name = Q_i.get('node_name')

            self.log(f'---------- _node_name: {_node_name} --- is_leaf: {is_leaf(Q_i)}')

            if not is_leaf(Q_i):
                qs = Q()
                _Q_ls = Q_i.get("Q_ls")
                qs = self._recursive_get_QS(_Q_ls, qs, _node_name)
                _add_logic = Q_i.get('add_logic')
                add_qs(QS, qs, _add_logic)

                # print('这个是复合条件, 需要递归处理 _node_name --- ', _node_name)
                self.log(f'*** _node_name: [{_node_name}] --- QS: [{QS}] --- \n\n')


            else:
                QS = self._QS_add_leaf_Q_i(QS, Q_i)

        if node_name is None:
            self.log(f'node_name[{node_name}] --- QS --- {QS} \n\n')
        return QS

    def get_QS(self, Q_ls=None):
        Q_ls = Q_ls if Q_ls is not None else self.Q_add_ls

        QS = self._recursive_get_QS(Q_ls)

        self.QS = QS
        return self.QS


class AdvancedSearchView(BaseListView):
    """
    高级检索

    POST /api/index/AdvancedSearch
    Q_add_ls = [
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

    # 简单列表检索的配置参考
    search_ls_dc = {
        "private_cn_classification_2_alpha": ["C5", "C3", "C4"],
    }

    search_conf = {
        "private_cn_classification_2_alpha": {
            "add_logic_external": "and",
            "add_logic_internal": "or",
            "accuracy": 1
        }
    }
    """
    _name = 'AdvancedSearchView'

    queryset = None
    serializer_class = None
    Q_ls = None

    # search_ls_dc的默认配置search_conf
    search_conf = None
    search_ls_dc = None
    DEFAULT_CONF = {
        'add_logic_external': 'and',  # list外部的合并逻辑
        'add_logic_internal': 'or',  # list内部的合并逻辑
        'accuracy': 1  # 匹配模式
    }

    search_condition_ls = None

    def post(self, request, *args, **kwargs):
        self._post_type = 'list'
        ret, status, msg = self.get_list_ret(request, *args, **kwargs)
        return APIResponse(ret, status=status, msg=msg)

    def get_Q_add_ls(self):
        key = 'Q_add_ls'
        ret_1 = self.get_key_from_query_dc_or_self(key, get_type='list')

        key = 'Q_ls'  # 兼容Q_ls
        ret_2 = self.get_key_from_query_dc_or_self(key, get_type='list')
        ret = ret_1 or ret_2
        return ret

    def get_search_condition_ls(self):
        key = 'search_condition_ls'
        ret = self.get_key_from_query_dc_or_self(key, get_type='list')
        return ret

    def get_queryset(self):
        query_dc = self.get_request_data()
        # ret = super().get_queryset()        # 默认返回所有
        ret = conv_to_queryset(self.queryset)

        search_ls_dc = self.get_key_from_query_dc_or_self('search_ls_dc')  # 将列表查询search_ls转换为Q_add_ls中的条件
        Q_add_ls = self.get_Q_add_ls()

        if Q_add_ls or search_ls_dc:
            # --- 将search_ls根据search_conf转化为Q_add_ls中的检索条件
            if search_ls_dc:
                if not Q_add_ls:
                    Q_add_ls = []

                search_conf = self.get_key_from_query_dc_or_self('search_conf')
                default_conf = self.DEFAULT_CONF.copy()

                for search_k, search_v in search_ls_dc.items():
                    my_api_assert_function(isinstance(search_v, list), f'search_ls_dc中{search_k}的值应为list类型!')
                    # print('~~~~~~~~~', search_k, search_v)
                    if search_conf:
                        conf_i = search_conf.get(search_k)
                        if conf_i:
                            default_conf.update(conf_i)
                        else:
                            self_search_conf = getattr(self, 'search_conf')
                            if isinstance(self_search_conf, dict) and self_search_conf.get(search_k):
                                conf_i = self_search_conf.get(search_k)
                                default_conf.update(conf_i)
                    # print(search_k, search_v, default_conf)

                    new_Q_ls = []
                    for v_i in search_v:
                        dc = {
                            "add_logic": default_conf.get('add_logic_internal'),
                            "search_field": search_k,
                            "search_keywords": v_i,
                            "accuracy": default_conf.get('accuracy'),
                        }
                        new_Q_ls.append(dc)

                    new_Q_dc = {
                        "add_logic": default_conf.get('add_logic_external'),
                        "Q_ls": new_Q_ls
                    }
                    Q_add_ls.append(new_Q_dc)

            add_q = AddQ(Q_add_ls=Q_add_ls)
            qs = add_q.get_QS()
            if not isinstance(ret, QuerySet):
                ret = get_base_queryset(ret)
            ret = ret.filter(qs)
            return ret

        search_condition_ls = query_dc.get('search_condition_ls', [])
        if search_condition_ls:
            search_condition_ls = self.get_search_condition_ls()
            # if search_condition_ls:
            #     if isinstance(search_condition_ls, str):
            #         search_condition_ls = json.loads(search_condition_ls)
            # else:
            #     search_condition_ls = self.search_condition_ls

            if isinstance(search_condition_ls, str):
                search_condition_ls = json.loads(search_condition_ls)

            if search_condition_ls:
                mcs = MultipleConditionSearch(self.queryset, search_condition_ls)
                mcs.add_multiple_conditions()
                ret = mcs.get_queryset()
            else:
                ret = super().get_queryset()

        return ret

