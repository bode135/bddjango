import re
from tqdm import tqdm
from bddjango import set_query_dc_value


def get_hot_research_keywords_dc_ls(queryset_qs_ls, kname='research_keywords_text', ret_num=50, dbg=False, stopwords=None, seq=';', duplicate_line_words=True):
    """
    得到热门的research_keywords

    - duplicate_line_words: 行内去重, 如['hello', 'word', 'hello', 'haha'], 只统计一次'hello'
    """
    # print('queryset_qs_ls ---', queryset_qs_ls)
    if isinstance(queryset_qs_ls, str):
        queryset = [{kname: queryset_qs_ls}]
    elif isinstance(queryset_qs_ls, dict):
        queryset = [queryset_qs_ls]
        dbg = False     # 1个的时候不能调试
    else:
        queryset = queryset_qs_ls.values(kname)

    # ---- 计算词频字典
    if stopwords is None:
        stopwords = []
    stopwords.extend(['安徽省', '安徽'])

    if dbg:
        total_i = tqdm(total=len(queryset), desc='生成词频字典...')

    words_dict = {}
    for q in queryset:

        if dbg:
            total_i.update(1)

        text_s = q.get(kname)
        if text_s:
            _text_s = re.split(seq, text_s)
            if duplicate_line_words:
                text_s = []
                # [text_s.append(i.strip()) if i.strip() not in text_s else None for i in _text_s]
                [text_s.append(i) if i not in text_s else None for i in _text_s]
            else:
                text_s = _text_s
            for word in text_s:
                if word:
                    # word = word.strip()
                    if word:
                        if word in stopwords or word == 'unknow':
                            continue
                        if word in words_dict.keys():
                            words_dict[word] += 1
                        else:
                            words_dict[word] = 1

    # 降序排序
    words_dict = sorted(words_dict.items(), key=lambda words_dict: words_dict[1], reverse=True)

    hot_research_keywords_dc_ls = []
    if dbg:
        total_i = tqdm(total=len(words_dict), desc='返回数据格式调整')
    for k, v in words_dict:
        if dbg:
            total_i.update(1)
        kv = {
            'name': k,
            'value': v,
        }
        hot_research_keywords_dc_ls.append(kv)

    hot_research_keywords_dc_ls = hot_research_keywords_dc_ls[:ret_num]
    return hot_research_keywords_dc_ls


def replace_field_to_regex_field(query_dc, field_name, sep=';', ret_reg=False):
    """
    # 将指定过滤字段转换为正则匹配过滤
    - 应用场景:
        `关键词`字段由符合的(诉讼法;民事诉讼法;刑事诉讼法)组成,
        而只想要(诉讼法), 不想要(民事诉讼法),
        则`__contains`已不满足需求,
        需要用正则表达式来实现精准匹配.

    :param query_dc: 请求字典, 如request.GET
    :param field_name: 要替换的过滤字段名
    :param sep: 分隔符
    :param ret_reg: True->返回替换好后的正则表达式, False->返回替换好的query_dc
    """
    field_value = query_dc.get(field_name)
    if not field_value:
        return query_dc

    if isinstance(sep, str) and (sep == '|' or '|' not in sep):
        reg = r'^' + field_value + sep + '|' + sep + field_value + sep + '|' + sep + field_value + '$' + r'|^' + field_value + '$'
    else:
        reg = ""
        sep_ls = sep if isinstance(sep, list) else sep.split('|')
        n = len(sep_ls)
        for i in range(n):
            sep_i = sep_ls[i]
            r_i = "("
            r_i += r'^' + field_value + sep_i + '|' + sep_i + field_value + sep_i + '|' + sep_i + field_value + '$' + r'|^' + field_value + '$'
            r_i += ")"
            if i < n - 1:
                r_i += '|'
            reg += r_i
    if ret_reg:
        return reg
    else:
        new_dc = {f"{field_name}__iregex": reg,
                  field_name: None}

        # if isinstance(query_dc, dict):
        #     query_dc.update(new_dc)
        # else:
        set_query_dc_value(query_dc, new_dc=new_dc)
        return query_dc

