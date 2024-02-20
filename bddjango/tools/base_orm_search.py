from django.db import models as m
from django.db.models import F
from django.http import JsonResponse
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib import admin
from bddjango.tools.extract_keyword import extract_keywords as _extract_keywords
from django.db.models.manager import BaseManager
from django.db.models.query import QuerySet
from bddjango.django.utils import get_total_occurrence_times_by_keywords


# region # --- 默认检索权重设置

"""
# --- 若WEIGHT_CONF不为None, 则默认值为0, 可实现单字段检索.

# Django默认用[D, C, B, A]代表该字段的权重
WEIGHT_CONF = {
    'D': 0.2,
    'C': 0.4,
    'B': 0.6,
    'A': 0.8,
}
"""

WEIGHT_CONF = {
    'D': 1,
    'C': 1,
    'B': 1,
    'A': 1,
}

RANK__GTE = 0.001        # 相关性检索过滤的最小值
GET_FREQUENCE = True     # 精确统计keywords出现的频数
# endregion


# region # --- 不需要改动的变量

search_conf_name = 'search_field_conf'        # 检索配置的字段名
search_vector_field_name = 'search_vector'      # 检索字段名
search_weight_name = 'search_weight_conf'        # 检索权重配置名
search_rank__gte = 'search_rank__gte'       # 关性检索过滤的最小值
search_rank_field_name = 'search_rank'


_WEIGHTS_ORDERING = ['D', 'C', 'B', 'A']       # Django权重的默认顺序, 不能乱改!

# endregion


def get_search_vector(search_conf, config="chinese_zh"):
    vector = None
    for k, v in search_conf.items():
        if vector:
            vector += SearchVector(k, weight=v, config=config)
        else:
            vector = SearchVector(k, weight=v, config=config)
    return vector


def extract_keywords(keywords, cut_all=False, topK=10):
    keywords = _extract_keywords.handle(keywords, cut_all=cut_all, topK=topK)
    return keywords


class SearchQuerySet(QuerySet):
    _weight_conf = None
    _rank__gte = None
    _search_get_frequence = None

    @property
    def search_get_frequence(self):
        if self._search_get_frequence is None:
            if hasattr(self.model, 'search_get_frequence'):
                self._search_get_frequence = getattr(self.model, 'search_get_frequence')
                assert self.search_get_frequence is not None, '`search_get_frequence`不能为None!'
            else:
                global GET_FREQUENCE
                self._search_get_frequence = GET_FREQUENCE
        return self._search_get_frequence

    @staticmethod
    def extract_keywords(keywords, cut_all=None):
        return extract_keywords(keywords, cut_all=cut_all)

    @property
    def search_vector_field_name(self):
        global search_vector_field_name
        return search_vector_field_name

    @property
    def search_rank_field_name(self):
        global search_rank_field_name
        return search_rank_field_name

    @property
    def weight_conf(self):
        if self._weight_conf is None:
            if hasattr(self.model, self.search_weight_name) and getattr(self.model, self.search_weight_name):
                self._weight_conf = getattr(self.model, self.search_weight_name)
            else:
                global WEIGHT_CONF
                self._weight_conf = WEIGHT_CONF
        return self._weight_conf

    @property
    def rank__gte(self):
        if self._rank__gte is None:
            if hasattr(self.model, self.search_rank__gte) and getattr(self.model, self.search_rank__gte):
                self._rank__gte = getattr(self.model, self.search_rank__gte)
            else:
                global RANK__GTE
                self._rank__gte = RANK__GTE
        return self._rank__gte

    @property
    def search_rank__gte(self):
        global search_rank__gte
        return search_rank__gte

    @property
    def search_conf_name(self):
        global search_conf_name
        return search_conf_name

    @property
    def search_weight_name(self):
        global search_weight_name
        return search_weight_name

    @property
    def weights_ordering(self):
        global _WEIGHTS_ORDERING
        return _WEIGHTS_ORDERING

    def search(self, keywords, queryset=None, weight_conf=None, cut_all=False, auto_order=True, rank__gte=None, rank_field_name=None, get_frequence=True, search_field_conf=None):
        """
        综合检索

        :param keywords: 检索关键词
        :param queryset: 基于该queryset进行检索, 默认全部
        :param weight_conf: 权重配置, 为空则使用模型的weight_conf, 模型的weight_conf为空则使用默认的`WEIGHT_CONF`
        :param cut_all: jieba的切词类型, 默认`search`. 取值: {"search": 浏览器检索, True: 全切, False: 简切}.
        :param auto_order: 自动按相关性大小(`search_rank_field_name`对应的值)排序
        :param rank__gte: 最小相关性, 为空则使用模型的对应属性, 模型对应属性为空则使用`RANK__GTE`
        :param rank_field_name: 返回时相关性排序的字段名, 一般为`search_rank`字段
        :param get_frequence: 是否精确统计关键词出现频数
        :return: 带有相关性排序的`queryset`
        """

        rank_field_name = rank_field_name if rank_field_name else self.search_rank_field_name

        _queryset = queryset if queryset is not None else self

        assert keywords is not None, 'keywords不能为空!'

        assert isinstance(keywords, (list, str)), 'keywords类型必须在[list, str]中!'
        keywords = extract_keywords(keywords, cut_all=cut_all) if isinstance(keywords, str) else keywords

        if hasattr(self.model, 'search_debug') and getattr(self.model, 'search_debug'):
            print(f"*** search ExtractKeywords: {keywords} --- cut_all: {cut_all}")

        search_conf = search_field_conf if search_field_conf else getattr(self.model, search_conf_name)
        assert search_conf, '必须在对应model指定检索配置search_conf参数, 即检索字段和对应权重的字典, 如{"title": 2, "summary": 1}'

        # 实现可以自定义权重的检索(包括前端层面自定义和各个模型层面自定义)
        _weight_conf = weight_conf if weight_conf is not None else self.weight_conf
        _values = list(search_conf.values())
        weights = []
        for v in _values:
            if isinstance(v, (int, float)):
                _v = v
            else:
                assert v in _weight_conf, f'权重值[{v}]配置可能有问题?'
                _v = _weight_conf.get(v)
            assert isinstance(_v, (int, float)), f'权重值[{v}]配置可能有问题?'
            weights.append(_v)

        search_field_ls = list(search_conf.keys())

        rank__gte = rank__gte if rank__gte is not None else self.rank__gte
        get_frequence = get_frequence if self.search_get_frequence is None else self.search_get_frequence

        queryset = get_total_occurrence_times_by_keywords(
            _queryset,
            search_field_ls,
            keywords=keywords,
            get_frequence=get_frequence,
            rank__gte=rank__gte,
            rank_field_name=rank_field_name,
            search_weight_ls=weights,
        )

        if auto_order:
            queryset = queryset.order_by(f'-{rank_field_name}', 'pk')

        return queryset


class SearchManager(BaseManager.from_queryset(SearchQuerySet)):

    @property
    def search_conf_name(self):
        global search_conf_name
        return search_conf_name


class BaseOrmSearchModel(m.Model):
    """
    # 全文检索类

    - 用户需要定义检索配置`search_field_conf`.
    - 可选
        - search_field_conf: 检索字段和字段权重
        - search_weight_conf: 自定义权重配置
        - search_rank__gte: 相关性过滤

    ---

    - eg:

    ```
    # 可以直接配置每个字段的权重
    search_field_conf = {
        'title': 1,
        'content': 0.1,
    }

    # 使用['A', 'B', 'C', 'D'], 兼容pg_search
    search_field_conf = {
        'title': 'A',
        'content': 'B',
    }
    search_weight_conf = {
        'A': 0.9,
        'B': 0.4,
    }

    search_rank__gte = 0.3
    ```
    """
    search_field_conf = None
    search_weight_conf = None
    search_rank__gte = 0.001

    search_debug = 0

    # use_base_orm_search_if_null_res = True      # 检索为空时, 启用基础orm检索再检索一遍A和B级别的字段
    # use_base_orm_search_count__lte = 100000      # 大于这个数量就关闭精确词频统计功能

    objects = SearchManager()

    @staticmethod
    def extract_keywords(keywords, cut_all=False):
        return extract_keywords(keywords, cut_all=cut_all)

    @property
    def search_vector_field_name(self):
        global search_vector_field_name
        return search_vector_field_name

    @property
    def search_rank_field_name(self):
        global search_rank_field_name
        return search_rank_field_name

    class Meta:
        abstract = True

