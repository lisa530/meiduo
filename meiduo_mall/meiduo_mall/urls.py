"""meiduo_mall URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url,include
from django.contrib import admin

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^', include('users.urls',namespace='users')),
    # 首页广告
    url(r'^', include('contents.urls',namespace='contents')),
    # 验证码
    url(r'^', include('verifications.urls')),
    # QQ登录
    url(r'^', include('oauth.urls')),
    # 省市区
    url(r'^', include('areas.urls')),
    # 商品
    url(r'^', include('goods.urls',namespace='goods')),
    # 购物车
    url(r'^', include('carts.urls',namespace='carts')),
    # 订单
    url(r'^', include('orders.urls',namespace='orders')),
    # 全文检索
    url(r'^search/', include('haystack.urls')),

]
