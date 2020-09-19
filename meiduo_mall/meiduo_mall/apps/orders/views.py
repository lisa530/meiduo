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
from django.core.paginator import Paginator, EmptyPage
from . import constants


class GoodsCommentView(View):
    """订单商品评价信息"""

    def get(self, request, sku_id):
        """展示详情页被评价的商品信息"""

        # 1. 获取评价后的订单商品信息(按最新评价的商品排序)
        order_goods_list = OrderGoods.objects.filter(sku_id=sku_id, is_commented=True).order_by('-create_time')[:30]
        # 2. 将订单商品对象构造成列表字典
        comment_list = []
        for order_goods in order_goods_list:
            username = order_goods.order.user.username # 多查一: 多类对象.外键 获取下单用户
            comment_list.append({
                # 通过 三目运算获取下单用户
                'username': username[0] + '***' + username[-1] if order_goods.is_anonymous else username,
                'comment': order_goods.comment, # 商品评价信息
                'score': order_goods.score, # 评分
            })

        # 返回响应对象
        return http.JsonResponse({'code':RETCODE.OK, 'errmsg':'OK', 'comment_list': comment_list})


class OrderCommentView(LoginRequiredMixin, View):
    """订单商品评价"""

    def get(self, request):
        """展示商品评价页面"""
        # 接收参数
        order_id = request.GET.get('order_id')
        user = request.user  # 获取登录用户
        # 校验order_id参数是否有效
        try:
            OrderInfo.objects.get(order_id=order_id, user=request.user)
        except OrderInfo.DoesNotExist:
            return http.HttpResponseNotFound('订单不存在')

        # 查询商品订单中未被评价的商品信息
        try:
            uncomment_goods = OrderGoods.objects.filter(order_id=order_id, is_commented=False)
        except Exception:
            return http.HttpResponseServerError('订单商品信息出错')

        # 构造待评价商品数据
        uncomment_goods_list = []
        for goods in uncomment_goods:
            uncomment_goods_list.append({
                'order_id': goods.order.order_id, # 订单id
                'sku_id': goods.sku.id,  # 多查一,多类对象.外键
                'name': goods.sku.name, # 商品名称
                'price': str(goods.price), # 商品价格
                'default_image_url': goods.sku.default_image.url,
                'comment': goods.comment, # 评价信息
                'score': goods.score, # 评分
                'is_anonymous': str(goods.is_anonymous), # 是否匿名评价
            })

        # 渲染模板
        context = {
            'skus': uncomment_goods_list
        }

        # 返回响应对象
        return render(request, 'goods_judge.html', context)

    def post(self, request):
        """保存评价订单商品"""

        # 1.接收参数(json)
        json_dict = json.loads(request.body.decode())
        order_id = json_dict.get('order_id')
        sku_id = json_dict.get('sku_id')
        score = json_dict.get('score')
        comment = json_dict.get('comment')
        is_anonymous = json_dict.get('is_anonymous')

        # 2. 检验所有参数
        if not all([order_id, sku_id, score, comment]):
            return http.HttpResponseForbidden('缺少必传参数')

        # 3. 查询订单信息, 条件为: 当前登录的用户, 订单状态为 待评价
        try:
            OrderInfo.objects.filter(order_id=order_id, user=request.user,
                                     status=OrderInfo.ORDER_STATUS_ENUM['UNCOMMENT'])
        except OrderInfo.DoesNotExist:
            return http.HttpResponseForbidden('参数order_id错误')
        # 4. 查询sku_id是否合格
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('参数sku_id错误')
        # 5. 判断是否是 匿名评价
        if is_anonymous:
            if not isinstance(is_anonymous, bool):
                return http.HttpResponseForbidden('参数is_anonymous错误')

        # 6.查询出未评价的订单商品数据,并为商品订单赋值
        OrderGoods.objects.filter(order_id=order_id, sku_id=sku_id, is_commented=False).update(
            comment=comment,  # 评价信息
            score=score,  # 评分
            is_anonymous=is_anonymous,  # 是否匿名
            is_commented=True  # 是否评价
        )

        #  累计sku商品评论数量
        sku.comments += 1
        sku.save()
        sku.spu.comments += 1
        sku.spu.save()

        # 如果所有订单商品都已评价，则修改订单状态为已完成
        if OrderGoods.objects.filter(order_id=order_id, is_commented=False).count() == 0:
            OrderInfo.objects.filter(order_id=order_id).update(status=OrderInfo.ORDER_STATUS_ENUM['FINISHED'])
        # 7. 返回响应对象
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


class UserOrderInfoView(LoginRequiredMixin, View):
    """我的订单"""

    def get(self, request, page_num):
        """提供我的订单页面"""
        # 获取当前登录用户
        user = request.user
        # 查询订单,按最新创建订单时间排序
        orders = user.orderinfo_set.all().order_by("-create_time")
        # 遍历所有订单
        for order in orders:
            # 绑定订单状态
            order.status_name = OrderInfo.ORDER_STATUS_CHOICES[order.status-1][1]
            # 绑定支付方式
            order.pay_method_name = OrderInfo.PAY_METHOD_CHOICES[order.pay_method-1][1]
            order.sku_list = []
            # 查询订单商品
            order_goods = order.skus.all()
            # 遍历订单商品
            for order_good in order_goods:
                sku = order_good.sku
                sku.count = order_good.count
                sku.amount = sku.price * sku.count
                order.sku_list.append(sku)

        # 分页
        page_num = int(page_num)
        try:
            # 实例化paginator对象,每页显示3条数据
            paginator = Paginator(orders, constants.ORDERS_LIST_LIMIT)
            # 获取当前所在页
            page_orders = paginator.page(page_num)
            total_page = paginator.num_pages # 总页数
        except EmptyPage:
            return http.HttpResponseNotFound('订单不存在')

        # 构造上下文
        context = {
            "page_orders": page_orders,
            'total_page': total_page,
            'page_num': page_num,
        }

        # 返回响应结果
        return render(request, "user_center_order.html", context)


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
    """提交订单"""

    def post(self, request):
        """保存订单基本信息和订单商品信息"""
        # 接收参数
        json_dict = json.loads(request.body.decode())
        address_id = json_dict.get('address_id')
        pay_method = json_dict.get('pay_method')

        # 校验参数
        if not all([address_id, pay_method]):
            return http.HttpResponseForbidden('缺少必传参数')
            # 判断address_id是否合法
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden('参数address_id错误')
        # 判断pay_method是否合法
        if pay_method not in [OrderInfo.PAY_METHODS_ENUM['CASH'], OrderInfo.PAY_METHODS_ENUM['ALIPAY']]:
            return http.HttpResponseForbidden('参数pay_method错误')

        # 明显的开启一次事务
        with transaction.atomic():
            # 在数据库操作之前需要指定保存点（保存数据库最初的状态）
            save_id = transaction.savepoint()

            # 暴力回滚
            try:
                # 获取登录用户
                user = request.user
                # 获取订单编号：时间+user_id == '20190526165742000000001'
                order_id = timezone.localtime().strftime('%Y%m%d%H%M%S') + ('%09d' % user.id)
                # 保存订单基本信息（一）
                order = OrderInfo.objects.create(
                    order_id = order_id,
                    user = user,
                    address = address,
                    total_count = 0,
                    total_amount = Decimal(0.00),
                    freight = Decimal(10.00),
                    pay_method = pay_method,
                    # status = 'UNPAID' if pay_method=='ALIPAY' else 'UNSEND'
                    status = OrderInfo.ORDER_STATUS_ENUM['UNPAID'] if pay_method == OrderInfo.PAY_METHODS_ENUM['ALIPAY'] else OrderInfo.ORDER_STATUS_ENUM['UNSEND']
                )

                # 保存订单商品信息（多）
                # 查询redis购物车中被勾选的商品
                redis_conn = get_redis_connection('carts')
                # 所有的购物车数据，包含了勾选和未勾选 ：{b'1': b'1', b'2': b'2'}
                redis_cart = redis_conn.hgetall('carts_%s' % user.id)
                # 被勾选的商品的sku_id：[b'1']
                redis_selected = redis_conn.smembers('selected_%s' % user.id)

                # 构造购物车中被勾选的商品的数据 {b'1': b'1'}
                new_cart_dict = {}
                for sku_id in redis_selected:
                    new_cart_dict[int(sku_id)] = int(redis_cart[sku_id])

                # 获取被勾选的商品的sku_id
                sku_ids = new_cart_dict.keys()
                for sku_id in sku_ids:

                    # 每个商品都有多次下单的机会，直到库存不足
                    while True:
                        # 读取购物车商品信息
                        sku = SKU.objects.get(id=sku_id) # 查询商品和库存信息时，不能出现缓存，所以没用filter(id__in=sku_ids)

                        # 获取原始的库存和销量
                        origin_stock = sku.stock
                        origin_sales = sku.sales

                        # 获取要提交订单的商品的数量
                        sku_count = new_cart_dict[sku.id]
                        # 判断商品数量是否大于库存，如果大于，响应"库存不足"
                        if sku_count > origin_stock:
                            # 库存不足，回滚
                            transaction.savepoint_rollback(save_id)
                            return http.JsonResponse({'code': RETCODE.STOCKERR, 'errmsg': '库存不足'})

                        # 模拟网络延迟
                        # import time
                        # time.sleep(7)

                        # SKU 减库存，加销量
                        # sku.stock -= sku_count
                        # sku.sales += sku_count
                        # sku.save()

                        new_stock = origin_stock - sku_count
                        new_sales = origin_sales + sku_count
                        result = SKU.objects.filter(id=sku_id, stock=origin_stock).update(stock=new_stock, sales=new_sales)
                        # 如果在更新数据时，原始数据变化了，返回0；表示有资源抢夺
                        if result == 0:
                            # 库存 10，要买1，但是在下单时，有资源抢夺，被买走1，剩下9个，如果库存依然满足，继续下单，直到库存不足为止
                            # return http.JsonResponse('下单失败')
                            continue

                        # SPU 加销量
                        sku.spu.sales += sku_count
                        sku.spu.save()

                        OrderGoods.objects.create(
                            order = order,
                            sku = sku,
                            count = sku_count,
                            price = sku.price,
                        )

                        # 累加订单商品的数量和总价到订单基本信息表
                        order.total_count += sku_count
                        order.total_amount += sku_count * sku.price

                        # 下单成功，记得break
                        break

                # 再加最后的运费
                order.total_amount += order.freight
                order.save()
            except Exception as e:
                transaction.savepoint_rollback(save_id)
                return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '下单失败'})

            # 数据库操作成功，明显的提交一次事务
            transaction.savepoint_commit(save_id)

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'order_id': order_id})


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

