from django.conf.urls import url
from . import views

urlpatterns = [
    # 查询省市区三级联动
    url(r'^areas/$',views.AreasView.as_view()),
]