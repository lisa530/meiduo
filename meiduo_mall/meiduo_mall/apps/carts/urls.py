from django.conf.urls import url
from . import views

urlpatterns = [
    # 添加购物车
    url(r'^carts/$',views.CartsView.as_view(),name='info'),

]