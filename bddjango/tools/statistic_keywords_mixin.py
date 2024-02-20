from django.core.cache import cache
from bddjango import get_count
from bddjango import set_query_dc_value
from bddjango.tools.get_hot_keywords import replace_field_to_regex_field


class StatisticKeywordsMixin:
    # --- 统计关键词
    statistic_keywords = False       # 是否默认统计关键词, 可由前端控制
    statistic_keywords__field_name = None       # 关键词字段
    statistic_keywords__sep = ";"       # 分隔符
    cache_expired_time__statistic_keywords = 0      # statistic_keywords的缓存时间

    statistic_keywords__ret_num = 40        # 返回数量
    get_accurate_results = True     # 是否精确统计
    cache_expired_time__get_count = 1       # count的缓存时间
    statistic_keywords__dbg = False     # 是否打印debug信息

    def get_list_queryset(self):
        query_dc = self.get_request_data()

        statistic_keywords__field_name = self.statistic_keywords__field_name

        key = f'{statistic_keywords__field_name}__contains'
        if key in query_dc:
            value = query_dc.get(key)
            set_query_dc_value(query_dc, {statistic_keywords__field_name: value, key: None})

        key = f'{statistic_keywords__field_name}__icontains'
        if key in query_dc:
            value = query_dc.get(key)
            set_query_dc_value(query_dc, {statistic_keywords__field_name: value, key: None})

        replace_field_to_regex_field(query_dc, statistic_keywords__field_name, sep=self.statistic_keywords__sep)

        return super().get_list_queryset()


    def get_keywords_pop_name_ls(self):
        """
        获取需要剔除的关键词
        """
        ret = []
        return ret

    def get_list_ret(self, request, *args, **kwargs):
        ret, status, msg = super().get_list_ret(request, *args, **kwargs)

        from bddjango.tools.get_hot_keywords import get_hot_research_keywords_dc_ls
        import pandas as pd
        from bddjango import conv_df_to_serializer_data
        from bddjango import zip_string_by_md5

        statistic_keywords = self.get_key_from_query_dc_or_self("statistic_keywords", "bool")
        statistic_keywords__ret_num = int(self.get_key_from_query_dc_or_self("statistic_keywords__ret_num"))

        if statistic_keywords:
            qs_ls = self.queryset
            field_name = self.statistic_keywords__field_name
            assert field_name, "属性statistic_keywords__field_name不能为空!"
            sep = self.statistic_keywords__sep

            dc_ls = {}

            _c_key = f"KeywordsStatistic2__{qs_ls.model._meta.object_name}__{field_name}__{sep}_{statistic_keywords__ret_num}"  # qs_ls = TitleBase.queryset && get_count
            c_key = zip_string_by_md5(_c_key)
            if self.cache_expired_time__statistic_keywords:
                dc_ls = cache.get(c_key, {})

            if not dc_ls:
                dc_ls = get_hot_research_keywords_dc_ls(qs_ls, field_name, seq=sep, ret_num=statistic_keywords__ret_num, dbg=self.statistic_keywords__dbg)
                # from bddjango import get_count, get_md5_query_for_qs_ls
                # from bddjango import zip_string_by_md5

                pop_name_ls = self.get_keywords_pop_name_ls() if hasattr(self, 'get_keywords_pop_name_ls') else []
                if pop_name_ls:
                    pop_index_ls = []
                    pop_index_i = 0
                    for dc_i in dc_ls:
                        v = dc_i.get('name').strip() if dc_i.get('name') else None
                        if v in pop_name_ls:
                            pop_index_ls.append(pop_index_i)
                        pop_index_i += 1
                    pop_index_ls.reverse()
                    for i in pop_index_ls:
                        dc_ls.pop(i)

                if self.get_accurate_results:
                    """
                    精确计算每个关键词的个数
                    """
                    from tqdm import tqdm
                    if self.statistic_keywords__dbg:
                        tqdm_i = tqdm(total=len(dc_ls))
                        tqdm_i.desc = f'词频精确统计中...'
                    get_accuracy_count = '__all__'

                    for dc_i in dc_ls:
                        name = dc_i.get('name')
                        if get_accuracy_count == '__all__' or name in get_accuracy_count:
                            field_value = name

                            # --- 正则
                            reg = replace_field_to_regex_field({field_name: field_value}, field_name, sep, True)
                            value = qs_ls.filter(**{f'{field_name}__iregex': reg}).count()

                            # --- 普通模糊匹配
                            # value = qs_ls.filter(**{f'{field_name}__icontains': field_value}).count()
                            # value = get_count(qs_ls.filter(**{f'{field_name}__icontains': field_value}),
                            #                   self.cache_expired_time__get_count)

                            if self.statistic_keywords__dbg:
                                tqdm_i.desc = f'[{field_value}]词频统计中...'
                                tqdm_i.update(1)

                            _v = dc_i['value']
                            if _v != value:
                                print(f'\n\n=== dc_i在字段name[{name}] = field_value[{field_value}]时不相等! _v[{_v}] != value[{value}]\n\n')

                            dc_i['value'] = value

                if dc_ls:
                    df = pd.DataFrame(dc_ls).sort_values(by='value', ascending=False)
                    dc_ls = conv_df_to_serializer_data(df)

                if self.cache_expired_time__statistic_keywords:
                    cache.set(c_key, dc_ls, self.cache_expired_time__statistic_keywords)
            ret['statistic_keywords'] = dc_ls
            ret['statistic_keywords__field_name'] = self.statistic_keywords__field_name

        return ret, status, msg
