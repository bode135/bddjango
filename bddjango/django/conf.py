from django.conf import settings


# --- 默认分页器参数设置 PAGINATION_SETTINGS
PAGINATION_SETTINGS = {
    'page_size': 10,       # 每页16个
    'page_size_query_param': 'page_size',       # 前端控制每页数量时使用的参数名, 'page_size'
    'page_query_param': 'p',        # 页码控制参数名"p"
    'max_page_size': 1000,      # 最大1000页
}

if hasattr(settings, 'PAGINATION_SETTINGS'):
    PAGINATION_SETTINGS.update(settings.PAGINATION_SETTINGS)


db_engine = settings.DATABASES.get('default').get('ENGINE')




