import os
import setuptools
import bddjango


dirname = 'bddjango'
version = bddjango.version()


# with open("Readme.md", "r", encoding='utf-8') as fh:
#     long_description = fh.read()


from m2r import parse_from_file
long_description = parse_from_file('Readme.md')


setuptools.setup(
    name=dirname,
    version=version,
    author="bode135",
    author_email='2248270222@qq.com',   # 作者邮箱
    description="常用的django开发工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://gitee.com/bode135/bdtools/tree/master/bddjango',   # 主页链接
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
