from django.conf.urls import url
from . import views

urlpatterns = [
    # 订单结算
    url(r'^orders/settlement/$', views.OrderSettlementView.as_view(),name='settlement'),
    # 提交订单
    url(r'^orders/commit/$', views.OrderCommitView.as_view()),
    # 提交订单成功
    url(r'^orders/success/$', views.OrderSuccessView.as_view()),
    # 我的订单
    url(r'^orders/info/(?P<page_num>\d+)/$', views.UserOrderInfoView.as_view(), name='info'),
    # 订单评价
    url(r'^orders/comment/$', views.OrderCommentView.as_view()),
    # 展示商品评价
    url(r'^comments/(?P<sku_id>\d+)/$',views.GoodsCommentView.as_view()),
]