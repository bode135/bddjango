from bddjango import get_base_model
from bddjango import get_base_queryset
from pgZhSearch import search_conf_name


class BaseFullTextSearchMixin:
    """
    # 基本全文检索Mixin

    - 启用全文检索: `search_keywords`
    """
    relevant_obj_search_fields = ['A', 'B']     # 自动检索指定等级的字段
    ret_original_data_if_not_exists = True      # 返回原始数据, 如果`search`的结果为空
    _name = 'BaseFullTextSearchView'

    def get_ordered_queryset(self):
        query_dc = self.get_request_data()
        keywords = query_dc.get('search_keywords')
        if keywords:
            ret = self.queryset.search(keywords)
        else:
            ret = super().get_ordered_queryset()
        return ret


class RelevantObjectRecommendationMixin(BaseFullTextSearchMixin):
    """
    # 相关对象推荐Mixin

    - 启用全文检索: `search_keywords`
    - 指定`relevant_id`, 推荐该对象的相关对象
    """

    use_relevant_id_param = True                # 是否启用本功能
    relevant_base_model = None                  # 要推荐的模型, 例如推荐指定`人物表`相关的`事件表`, 默认为自身
    relevant_obj_search_fields = None           # 指定检索字段
    relevant_obj_search_levels = ['A', 'B']     # 若未指定`relevant_obj_search_fields`, 将自动选择指定等级的字段
    ret_original_data_if_not_exists = True      # 返回原始数据, 如果`search`的结果为空

    def get_ordered_queryset(self):
        ret = super().get_ordered_queryset()

        param_name = 'relevant_id'
        query_dc = self.get_request_data()

        if self.use_relevant_id_param and param_name in query_dc:
            relevant_id = query_dc.get(param_name)
            obj = get_base_queryset(ret).get(id=relevant_id)        # 这个得在全局检索
            ret = ret.exclude(id=relevant_id)
            qs_ls_0 = ret       # 万一没检索到相关结果, 就返回这个
            base_model = self.relevant_base_model if self.relevant_base_model else get_base_model(self.queryset)
            assert hasattr(base_model, search_conf_name), f'base_model[{base_model}]没有search_conf_name[{search_conf_name}]!'

            relevant_obj_search_fields = self.relevant_obj_search_fields
            if relevant_obj_search_fields is None:
                # 找出['A', 'B']等级的字段
                relevant_obj_search_fields = [k for k, v in getattr(base_model, search_conf_name).items() if v in self.relevant_obj_search_levels]

            search_keywords = None
            for sf in relevant_obj_search_fields:
                _value = f' {getattr(obj, sf)} '
                if search_keywords is None:
                    search_keywords = _value
                else:
                    search_keywords += _value
            ret = ret.search(search_keywords)
            if self.ret_original_data_if_not_exists and not ret.exists():
                # print(f"--- relevant_search: ret not exists! relevant_id: {relevant_id}")
                ret = qs_ls_0       # 返回相关检索之前进行过基本字段过滤的queryset
        return ret





