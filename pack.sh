#!/usr/bin/env bash

# 环境配置: python -m pip install setuptools wheel twine

rm -rf dist
python setup.py sdist bdist_wheel
twine upload dist/*