from django.shortcuts import render
from django.views import View
import json,base64,pickle
from django import http
from goods.models import SKU
from django_redis import get_redis_connection

from meiduo_mall.utils.response_code import RETCODE


class CartsView(View):
    """购物车管理"""

    def post(self,request):
        """保存购物车"""
        # 接收参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        # 没有传递参数，取后面的参数
        selected = json_dict.get('selected', True) # 可选

        # 校验参数
        # 判断参数是否齐全
        if not all([sku_id,count]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 校验sku_id是否合法
        try:
            SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('参数sku_id错误')
        # 校验count是否为整数
        try:
            count = int(count)
        except Exception as e:
            return http.HttpResponseForbidden('参数count错误')
        # 校验勾选是否是bool
        if selected:
            # 第一个参数是 对象， 第二个参数是：类型
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected错误')

        # 判断用户是否登录
        user = request.user
        if user.is_authenticated:
            # 用户已登录,购物车数据存储到redis
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            # 需要以增量计算的形式保存商品数据(hash)
            # hash表中有一个命令 hincrby用于为哈希表中的指定字段的整数值加上增
            pl.hincrby('carts_%s' % user.id, sku_id,count)
            # 保存商品勾选状态
            if selected:
                pl.sadd('selected_%s' % user.id, sku_id)
            # 执行
            pl.execute()
            # 响应结果
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})
        else:

            # 用户未登录,获取cookie中的购物车数据，并且判断是否有购物车数据
            cart_str = request.COOKIES.get('carts')
            if cart_str: # 将字符串类型转为真正字典
                # 将cart_str转成bytes类型的字符串
                cart_str_bytes = cart_str.encode()
                # 将cart_str_bytes转成bytes类型字典
                cart_dict_bytes = base64.b64decode(cart_str_bytes)
                # 将cart_dict_bytes转成真正的字典
                cart_dict = pickle.loads(cart_str_bytes)
            else: # cookie中没有购物车数据
                cart_dict = {}

            # 判断当前要添加的商品在cart_dict中是否存在
            if sku_id in cart_dict:

                """ 登录用户购物车数据结构
                {
                    sku_id:{
                    count:"1",
                    selected:"True"
                }
                """
                # 购物车已存在，增量计算
                origin_count = cart_dict[sku_id]['count']
                count += origin_count # 将原有数据进行相加

            # 购物车不存在，构造购物车cookie数据结构
            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }

            # 保存购物车数据
            # 将cart_dict转成bytes类型的字典
            cart_dict_bytes = pickle.dumps(cart_dict)
            # 将cart_dict_bytes进行编码，得到编码后的bytes类型的字符串
            cart_str_bytes = base64.b64encode(cart_dict_bytes)
            # 将cart_str_bytes进行解码，得到解码后的字符串
            cookie_cart_str = cart_str_bytes.decode()

            response = http.JsonResponse({'code': RETCODE.OK,'errmsg':'OK'})
            response.set_cookie('carts', cookie_cart_str)

            # 响应结果
            return response
