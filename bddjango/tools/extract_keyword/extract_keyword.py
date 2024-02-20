# -*- coding: utf-8 -*-
"""
基于gensim模块的中文句子相似度计算

思路如下：
1. 分词
2. 去停用词
3. 关键词提取
"""

import jieba
import jieba.analyse
import os


class ExtractKeywords(object):
    """

    :param ori_text:
    :return:
    """

    def __init__(self, ori_text=None, _stopwords_path=None, cut_all='search', _user_dict_path=None, _synonym_dict_path=None):
        """
        初始化

        - _stopwords_path: 停用词词表
        - _user_dict_path: 自定义词表
        - cut_all: 默认切词方式, ['search', True, False] -> [浏览器切词, 全切, 简切]
        """
        self.ori_text = ori_text
        self.cut_all = cut_all

        current_dir_path = os.path.dirname(__file__)
        self._stopwords_path = os.path.join(current_dir_path,
                                            'stopwords.txt') if _stopwords_path is None else _stopwords_path

        self._user_dict_path = os.path.join(current_dir_path,
                                            'user_dict.txt') if _user_dict_path is None else _user_dict_path

        self._synonym_dict_path = os.path.join(current_dir_path,
                                            'synonym_dict.txt') if _synonym_dict_path is None else _synonym_dict_path

    @staticmethod
    def get_stop_word(_stopwords_path):
        """
        获取停用词
        :stopwords_path:
        :return:
        """
        stopwords = set()
        file = open(_stopwords_path, 'r', encoding='UTF-8')
        for line in file:
            stopwords.add(line.strip())
        file.close()
        return stopwords

    _loaded_user_dc = False

    _loaded_synonym_dc = False

    _stopwords_set = None

    @property
    def stopwords_set(self):
        if not self._stopwords_set:
            self._stopwords_set = self.get_stop_word(self._stopwords_path)
        return self._stopwords_set

    def reset_stopwords_set(self, fpath):
        self._stopwords_set = self.get_stop_word(fpath)

    _user_dict = None
    _synonym_dc = None

    # @property
    # def user_dict(self):
    #     if not self._user_dict:
    #         self._user_dict = self.get_stop_word(self._user_dict_path)
    #     return self._user_dict

    def load_user_dict(self, fpath):
        # self._user_dict = self.get_stop_word(fpath)
        self._user_dict_path = fpath
        self._loaded_user_dc = False

    @property
    def synonym_dc(self):
        if not self._loaded_synonym_dc and not self._synonym_dc:
            # 1读取同义词表，并生成一个字典。
            combine_dict = {}
            # synonymWords.txt是同义词表，每行是一系列同义词，用空格分割
            for line in open(self._synonym_dict_path, "r", encoding='utf-8'):
                seperate_word = line.strip().split(" ")
                num = len(seperate_word)
                for i in range(1, num):
                    combine_dict[seperate_word[i]] = seperate_word[0]
                # print(seperate_word)
            # print(combine_dict)
            self._synonym_dc = combine_dict
            self._loaded_synonym_dc = True
        return self._synonym_dc

    def handle(self, ori_text=None, cut_all=None, topK=10):
        # print("--- ori_text:", ori_text)
        if not self._loaded_user_dc:       # 是否已加载自定义词典
            jieba.load_userdict(self._user_dict_path)
            self._loaded_user_dc = True

        # step1: break down words
        # 精确模式
        # print(self.ori_text)
        if ori_text is None:
            ori_text = self.ori_text

        if cut_all is None:
            cut_all = self.cut_all

        if cut_all == 'search':
            cut_text = jieba.cut_for_search(ori_text)
        else:
            cut_text = jieba.cut(ori_text, cut_all=cut_all)

        # step2：去停用词
        # 这里是有一个文件存放要改的文章，一个文件存放停用表，然后和停用表里的词比较，一样的就删掉，最后把结果存放在一个文件中
        # stopwords_set = self.get_stop_word(self._stopwords_path)

        use_synonym_dc = False
        if self.synonym_dc:
            use_synonym_dc = True

        final = ""
        for word in cut_text:
            # --- 替换同义词
            if use_synonym_dc and word in self.synonym_dc:
                word = self.synonym_dc[word]
            if word not in self.stopwords_set:
                if final:
                    final = final + " " + word
                else:
                    final = word
        # print(f'--- [{ori_text}]的`分词`结果: [{final}]')

        # step3：提取关键词
        # res = jieba.analyse.extract_tags(final, topK=5, withWeight=True, allowPOS=())
        # n	普通名词	f	方位名词	s	处所名词	t	时间
        # nr	人名	ns	地名	nt	机构名	nw	作品名
        # nz	其他专名	v	普通动词	vd	动副词	vn	名动词
        # a	形容词	ad	副形词	an	名形词	d	副词
        # m	数量词	q	量词	r	代词	p	介词
        # c	连词	u	助词	xc	其他虚词	w	标点符号
        # PER	人名	LOC	地名	ORG	机构名	TIME	时间

        res = jieba.analyse.extract_tags(final, topK=topK,
                                         allowPOS=('n', 'f', 's', 'nr', 'ns', 'nt', 'nw', 'nz', 'v', 'vn', 'an',
                                                   'PER', 'LOC', 'ORG'))

        # print(f'--- [{ori_text}]的`extract_tags`结果: [{final}]')

        # res = jieba.analyse.extract_tags(final, topK=10)
        # res = final

        # text 为待提取的文本
        # topK:返回几个 TF/IDF 权重最大的关键词，默认值为20。
        # withWeight:是否一并返回关键词权重值，默认值为False。
        # allowPOS:仅包括指定词性的词，默认值为空，即不进行筛选。
        if res:
            # 添加本身不分词的短语或句子
            if len(res) < topK and ori_text not in res and len(ori_text) <= 4:
                res.insert(0, ori_text)
            return res
        else:
            return [ori_text]


extract_keywords = ExtractKeywords()

if __name__ == "__main__":
    ori_text = '城市绿化是栽种植物以改善城市环境的活动。 ' \
               '城市绿化作为城市生态系统中的还原组织 ' \
               '城市生态系统具有受到外来干扰和破坏而恢复原状的能力，' \
               '就是通常所说的城市生态系统的还原功能。'
    ori_text2 = '信息安全事故'
    # ori_text2 = '特大安全事故'
    # ori_text2 = '安全'
    # ori_text2 = '事故'
    # _stopwords_path = r'E:\AProject\EmergencyManagement_dj2201\common_app\common\stopwords.txt'
    # _stopwords_path = r'G:\PycharmProjects\yingJiGuanLiXiTong_dj2201\common_app\common\stopwords.txt'
    a = ExtractKeywords(ori_text2)
    res = a.handle()
    print(type(res), res)
