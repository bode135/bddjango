# bddjango
> django常用开发工具

## 安装  

```
pip install bddjango
```

## 功能

- admin界面数据管理功能

  > 能够解析excel和csv文件

  - 上传
    - 导入时支持DateField和DateTimeField, 暂不支持外键类的解析
  - 下载
    - 导出数据时试用verbose_name中文列名
  - 保存
    - 解决了导入数据后, 保存时主键冲突的bug

- 将DRF常用View功能打包为BaseList基础类

  - 列表页
    - 排序
    - 分页
    - 过滤
  - 详情页

- admin界面

  > 和simpleui一起用

  - 导入数据界面
  - 导出数据界面

## 备注
- admin管理的模型主键必须为`id`, 不然会出错.

- https://realpython.com/pypi-publish-python-package/
