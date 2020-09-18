from django.utils import timezone
from datetime import datetime
from django.shortcuts import render
from django.views import View
from meiduo_mall.utils.views import LoginRequiredMixin,LoginRequiredJSONMixin
from django_redis import get_redis_connection
from decimal import Decimal
import json
from django import http
from django.db import transaction

from meiduo_mall.utils.response_code import RETCODE
from orders.models import OrderInfo,OrderGoods
from users.models import Address
from goods.models import SKU


class OrderSuccessView(LoginRequiredMixin, View):
    """提交订单成功页面"""

    def get(self,request):
        """提供提交订单成功页面"""
        order_id = request.GET.get('order_id')
        payment_amount = request.GET.get('payment_amount')
        pay_method = request.GET.get('pay_method')

        context = {
            'order_id': order_id,
            'payment_amount': payment_amount,
            'pay_method': pay_method
        }

        return render(request, 'order_success.html', context)


class OrderCommitView(LoginRequiredJSONMixin, View):
    """订单提交"""

    def post(self, request):
        """保存订单信息和订单商品信息"""
        # 1. 接收参数,校验参数
        json_dict = json.loads(request.body.decode())
        address_id = json_dict.get('address_id')
        pay_method = json_dict.get('pay_method')

        # 校验参数是否完整
        if not all([address_id, pay_method]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 判断address_id是否合法
        try:
            address = Address.objects.get(id=address_id)
        except Exception:
            return http.HttpResponseForbidden('参数address_id错误')
        # 判断pay_method是否合法
        if pay_method not in [OrderInfo.PAY_METHODS_ENUM['CASH'], OrderInfo.PAY_METHODS_ENUM['ALIPAY']]:
            return http.HttpResponseForbidden('参数pay_method错误')

        # 明显的开启一次事务
        with transaction.atomic():
            # 在数据库操作之前需要指定保存点（保存数据库最初的状态）
            save_id = transaction.savepoint()
            try:
                # 2. 获取登录用户
                user = request.user
                # 3. 生成订单编号: 年月日时分秒+用户编号
                # timezone.localtime获取当前时间,strftime将时间对象转为时间字符串 拼接上 user_id
                order_id = timezone.localtime().strftime('%Y-%m-%d-%H-%M-%S') + ('%09d' % user.id)
                # 4. 保存订单基本信息
                order = OrderInfo.objects.create(
                    order_id=order_id,  # 订单id
                    user=user,  # 当前登录用户
                    address=address,  # 收货地址
                    total_count=0,  # 总数量
                    total_amount=Decimal(0.00),  # 总金额
                    freight=Decimal(10.00),  # 运费
                    pay_method=pay_method,  # 支付方式
                    # status = 'UNPAID' if pay_method=='ALIPAY' else 'UNSEND'
                    # 订单状态
                    status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'] if pay_method == OrderInfo.PAY_METHODS_ENUM['ALIPAY'] else
                    OrderInfo.ORDER_STATUS_ENUM['UNSEND']
                )

                # 5. 保存订单商品信息
                # 从redis读取购物车中被勾选的商品信息
                redis_conn = get_redis_connection('carts')
                redis_cart = redis_conn.hgetall('carts_%s' % user.id)  # 所有的购物车数据，包含了勾选和未勾选 ：{b'1': b'1', b'2': b'2'}
                # 获取购物车中全选的商品sku_id [b'1']
                redis_selected = redis_conn.smembers('selected_%s' % user.id)

                # 构造购物车选中商品数据 {b'1': b'1'}
                new_cart_dict = {}
                # 遍历购物车中被选中的商品
                for sku_id in redis_selected:
                    # 取出购物车中所有数据, (sku_id count) 赋值给new_cart_dict
                    new_cart_dict[int(sku_id)] = int(redis_cart[sku_id])

                # 获取被勾选的商品的sku_id和count
                sku_ids = new_cart_dict.keys()  # 取出字典中所有的key : sku_id count
                for sku_id in sku_ids:  # 遍历购物车中被勾选的商品信息

                    # 每个商品都有多次下单的机会，直到库存不足
                    while True:
                        # 查询SKU信息
                        sku = SKU.objects.get(id=sku_id)

                        # 获取原有的库存和销量
                        origin_stock = sku.stock
                        origin_sales = sku.sales

                        # 获取要提交的订单的商品数量
                        sku_count = new_cart_dict[sku_id]
                        #  库存不足,回滚
                        if sku_count > sku.stock:
                            transaction.savepoint_rollback(save_id)
                            return http.JsonResponse({'code': RETCODE.STOCKERR, 'errmsg': '库存不足'})

                        # 模拟网络延迟
                        import time
                        time.sleep(7)

                        # SKU 减少库存，加销量
                        # sku.stock -= sku_count
                        # sku.sales += sku_count
                        # sku.save()

                        # SKU 减少库存，加销量
                        new_stock = origin_stock - sku_count # 原有库存 - 原有数量
                        new_sales = origin_sales + sku_count # 原有销量 + 原有数量

                        # 使用乐观锁更新和销量
                        # 使用原有数据为条件，查询是否有人修改库存记录，得到原有数据结果，使用新的存和销量覆盖原有的
                        result = SKU.objects.filter(id=sku_id,stock=origin_stock).update(stock=new_stock, sales=new_sales)

                        # 库存 10，要买1，但是在下单时，有资源抢夺，被买走1，剩下9个，如果库存依然满足，继续下单，直到库存不足为止
                        if result == 0:  # result表示sql语句修改数据的个数
                            continue

                        # SPU 加销量
                        sku.spu.sales += sku_count # 一查多: 一个sku对应多个spu
                        sku.spu.save()

                        # 保存订单商品信息
                        OrderGoods.objects.create(
                            order=order,  # 关联的订单对象
                            sku=sku,  # 订单商品
                            count=sku_count,  # 商品数量
                            price=sku.price,  # 商品价格
                        )

                        # 累加商品订单的数量和总价到订单基本信息表
                        order.total_count += sku_count
                        order.total_amount += sku_count * sku.price
                        # 下单成功,记得brack
                        break

                # 再加最后的运费
                order.total_amount += order.freight
                order.save()

            except Exception as e: # 数据库操作失败,回滚
                transaction.savepoint_rollback(save_id)
                return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '下单失败'})

            # 数据库操作成功：提交一次事务
            transaction.savepoint_commit(save_id)

        return http.JsonResponse({'code': RETCODE.OK,'errmsg':'OK',})


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

