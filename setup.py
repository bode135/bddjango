import os
import setuptools
import bddjango
from m2r import parse_from_file


dirname = 'bddjango'
version = bddjango.version()
# print("version ================ ", version)


# with open("PypiReadme.md", "r", encoding='utf-8') as fh:
#     long_description = fh.read()
long_description = parse_from_file('PypiReadme.md')     # .markdown必须转换为.rst, 否则有可能报错


setuptools.setup(
    name=dirname,
    version=version,
    author="bode135",
    author_email='2248270222@qq.com',   # 作者邮箱
    description="常用的django开发工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/bode135/bddjango.git',   # 主页链接
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=['pandas', 'django', 'openpyxl', 'xlrd==1.2.0', 'bdtime', 'tqdm'],      # 依赖模块
    include_package_data=True,
)
