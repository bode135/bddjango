"""
迁移出错时用的虚假模型
"""


class FakeModel:
    class Meta:
        abstract = False
        swapped = True
        fields = []
    _meta = Meta
