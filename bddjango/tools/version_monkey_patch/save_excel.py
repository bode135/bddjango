"""
对高版本pandas的to_excel方法进行兼容
"""
import inspect


def get_params_of_func(func):
    # 获取函数的签名对象
    signature = inspect.signature(func)
    # 提取参数名并返回
    return [param.name for param in signature.parameters.values()]


def save_excel(df, f_path):
    if 'encoding' not in get_params_of_func(df.to_excel):
        df.to_excel(f_path, index=False)  # 新版pandas取消了`encoding`参数
    else:
        df.to_excel(f_path, index=False, encoding='utf-8')


if __name__ == '__main__':
    # 测试
    def func1(a, b, test=3):
        pass

    def func2(a, b):
        pass

    print(get_params_of_func(func1))  # 输出: ["a", "b", "c"]
    print(get_params_of_func(func2))  # 输出: ["a", "b"]


