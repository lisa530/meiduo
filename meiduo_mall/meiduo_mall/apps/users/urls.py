from django.conf.urls import url
# from .views import RegisterView
from . import views

urlpatterns = [
    # 用户注册: reverse(users:register) == '/register/'
    url(r'^register/$', views.RegisterView.as_view(), name='register'),
    # 用户名是否重复注册
    url(r'^usernames/(?P<username>[a-zA-Z0-9_-]{5,20})/count/$', views.UsernameCountView.as_view()),
    # 手机号是否重复注册
    url(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$', views.MobileCountView.as_view()),

    # 用户登录
    url(r'^login/$', views.LoginView.as_view(), name='login'),
    # 退出登录
    url(r'^logout/$', views.LogOutView.as_view(), name='logout'),
    # 用户中心
    url(r'^info/$', views.UserInfoView.as_view(), name='info'),
    # 添加邮箱
    url(r'^emails/$', views.EmailView.as_view()),
    # 验证邮箱
    url(r'^emails/verification/$', views.VerifyEmailView.as_view()),
    # 展示收货地址
    url(r'^addresses/$',views.AddressView.as_view(),name='address'),
    # 新增收货地址
    url(r'^addresses/create/$',views.AddressCreateView.as_view()),
    # 更新和删除地址
    url(r'^addresses/(?P<address_id>\d+)/$',views.UpdateDestoryAddressView.as_view()),
    # 设置默认收货地址
    url(r'^addresses/(?P<address_id>\d+)/default/$',views.DefaultAddressView.as_view())
]