"""
自定义字段类型
"""
from django.db import models


class AliasField(models.Field):
    """
    绑定字段, 在使用特定函数时, 统一参数.
    """
    def contribute_to_class(self, cls, name, private_only=False):
        """
        virtual_only is deprecated in favor of private_only
        """
        super(AliasField, self).contribute_to_class(cls, name, private_only=True)
        setattr(cls, name, self)

    def __get__(self, instance, instance_type=None):
        return getattr(instance, self.db_column)