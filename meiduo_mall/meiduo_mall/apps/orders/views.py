from django.shortcuts import render
from django.views import View
from meiduo_mall.utils.views import LoginRequiredMixin
from users.models import Address
from goods.models import SKU
from django_redis import get_redis_connection
from decimal import Decimal

from meiduo_mall.utils.response_code import RETCODE


class OrderSettlementView(LoginRequiredMixin,View):
    """结算订单"""

    def get(self,request):
        """查询并展示要结算的订单数据"""
        # 获取登录用户
        user = request.user
        # 查询用户收货地址：查询登录的用户地址没有删除的
        try:
            addresses = Address.objects.filter(user=user, is_deleted=False)
        except Exception as e:
            # 如果没有查询出地址，可以去编辑收货地址
            addresses = None

        # 查询出redis购物车被选中的商品
        redis_conn = get_redis_connection('carts')
        # 所有的购物车数据，包含了勾选和未勾选 ：{b'1': b'1', b'2': b'2'}
        redis_cart = redis_conn.hgetall('carts_%s' % user.id)
        # 被选中的商品sku_id:[b:'1']
        redis_selected = redis_conn.smembers('selected_%s' % user.id)

        # 构造购物车中被勾选的商品的数据 {b'1': b'1'}
        new_cart_dict = {}
        for sku_id in redis_selected:  # 遍历被选中的sku_id
            # 取出全选sku_id 赋值给新字典
            new_cart_dict[int(sku_id)] = int(redis_cart[sku_id])

        # 获取被勾选的商品的sku_id
        sku_ids = new_cart_dict.keys() # 取出所有的key
        skus = SKU.objects.filter(id__in=sku_ids) # 查询条件为id在sku_ids列表中的skus

        # 给总金额/总数量赋值
        total_count = 0
        total_amount = Decimal(0.00)  # 将totoal_amount类型设置为Decimal

        #  遍历skus
        for sku in skus:
            # 使用面对对象的方式：给每个sku绑定count（数量）和amount（小计）
            sku.count = new_cart_dict[sku.id]
            sku.amount = sku.price * sku.count  # price字段为Decimal类型的

            # 每遍历一次，累加数量和金额
            total_count += sku.count
            total_amount += sku.amount

        # 指定默认的邮费
        freight = Decimal(10.00)

        # 构造上下文
        context = {
            'addresses': addresses, # 默认收货地址
            'skus': skus, # 商品列表
            'total_count': total_count, # 总数量
            'total_amount': total_amount, # 总金额
            'freight': freight, # 运费
            'payment_amount': total_amount + freight, # 实付款
        }
        return render(request, 'place_order.html', context)

