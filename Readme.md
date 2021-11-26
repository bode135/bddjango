# bddjango
> drf+postgresql+simpleui环境下的常用开发工具

## 安装  

```
pip install bddjango
```

## 功能

- admin界面
  > 和simpleui一起用

  - 导入数据界面
  - 导出数据界面
  - 修复了部分bug
    > 导入之后就自动修复. 并且和base版django-admin界面兼容.  
    - [刚进入表格后, 表的右上方蓝色字体"选中所有"点击不生效](https://github.com/newpanjing/simpleui/issues/408)
    - [actions无法和objects解绑 ](https://github.com/newpanjing/simpleui/issues/404)
    - [使用django-guardian对象级别权限管理后，“对象权限”按钮和页面不美观](https://gitee.com/tompeppa/simpleui/issues/I1P2X4)
  - 未解决问题:
    - [按回车无法跳页](https://github.com/newpanjing/simpleui/issues/408)

- admin界面数据管理功能

  > 能够解析excel和csv文件

  - 上传
    - 导入时支持DateField和DateTimeField, 暂不支持外键类的解析
  - 下载
    - 导出数据时试用verbose_name中文列名
  - 保存
    - 解决了postgresql导入数据后, 保存时主键冲突的bug

- 将DRF常用View功能打包为BaseList基础类
  - 列表页
    - 排序
    - 分页
    - 过滤
  - 详情页
  - 高级检索
  - 权限控制


## 备注

- https://realpython.com/pypi-publish-python-package/
