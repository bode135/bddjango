import sys

print(f'sys.version: {sys.version}')

import inspect

def get_params_of_func(func):
    # 获取函数的签名对象
    signature = inspect.signature(func)
    # 提取参数名并返回
    return [param.name for param in signature.parameters.values()]


class A:
    def func1(self, a, b, c):
        pass

    def func2(self, a, b):
        pass


# 测试
def func1(a, b, c):
    pass

def func2(a, b):
    pass

a = A()
print(get_params_of_func(func1))  # 输出: ["a", "b", "c"]
print(get_params_of_func(func2))  # 输出: ["a", "b"]
print(get_params_of_func(a.func1))  # 输出: ["a", "b"]
print(get_params_of_func(a.func2))  # 输出: ["a", "b"]
