from django.conf.urls import url
# from .views import RegisterView
from . import views

urlpatterns = [
    # 首页
    url(r'^$', views.IndexView.as_view(), name='index'),
]