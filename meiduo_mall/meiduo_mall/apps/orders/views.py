from django.shortcuts import render
from django.views import View
from meiduo_mall.utils.views import LoginRequiredMixin

# Create your views here.


class OrderSettlementView(LoginRequiredMixin,View):
    """结算订单"""

    def get(self,request):
        """查询并展示要结算的订单数据"""
        return render(request, 'place_order.html')