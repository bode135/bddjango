from django.urls import path, re_path
from . import views, tests
# from revproxy.views import ProxyView
# from django.conf.urls import patterns, include,url


app_name = "file_upload"
urlpatterns = [
    re_path(r'^ImportExportData(/$|/(?P<pk>\w+)/$)', views.ImportExportData.as_view()),
    re_path(r'^FileSelection(/$|/(?P<pk>\w+)/$)', views.FileSelection.as_view()),
    re_path(r'^UploadFile(/$|/(?P<pk>\w+)/$)', views.UploadFile.as_view()),
    re_path(r'^DownLoadFile(/$|/(?P<pk>\w+)/$)', views.DownLoadFile.as_view()),
    re_path(r'^Doc(/$|/(?P<pk>\w+)/$)', views.Doc.as_view()),
    re_path(r'^Search(/$|/(?P<pk>\w+)/$)', views.Search.as_view()),
    re_path(r'^WebSSH(/$|/(?P<pk>\w+)/$)', views.WebSSH.as_view()),
]
