"""ControlHub URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from . import views


urlpatterns = [
    path('api/admin/', admin.site.urls),

    re_path('api/media/(?P<path>.*)', serve, {"document_root": settings.MEDIA_ROOT}),  # 静态文件media模块
    re_path('api/static/(?P<path>.*)', serve, {"document_root": settings.STATIC_ROOT}),  # 静态文件static模块

    path('api/test/', views.Test.as_view()),  # simpleui的前缀

    path('api/file_upload/', include('file_upload.urls')),
    path('api/index/', include('index.urls')),
]

if settings.USE_SIMPLE_UI:
    urlpatterns.append(path('api/home/', views.HomeChartView.as_view())),  # simpleui的前缀

