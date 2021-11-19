#!/usr/bin/env bash
: 初始化项目环境, 部署用
: 用conda管理python版本: https://zhuanlan.zhihu.com/p/36386617, conda create -name py36 python=3.6, source activate py36

: 创建虚拟环境
virtualenv --python=python3.6 venv

: 加载虚拟环境
source venv/bin/activate
: venv/Scripts/activate.bat

: 克隆仓库
git clone https://gitee.com/LoongText/thinkTank_dj2006.git -b bode

