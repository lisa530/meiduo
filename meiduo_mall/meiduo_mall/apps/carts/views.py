from django.shortcuts import render
from django.views import View
import json,base64,pickle
from django import http
from goods.models import SKU
from django_redis import get_redis_connection

from meiduo_mall.utils.response_code import RETCODE


class CartsSelectAllView(View):
    """全选购物车"""

    def put(self, request):
        # 接收参数
        json_dict = json.loads(request.body.decode())
        selected = json_dict.get('selected', True)

        # 校验参数
        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')

        # 判断用户是否登录
        user = request.user
        if user.is_authenticated:
            # 用户已登录，操作redis购物车
            redis_conn = get_redis_connection('carts')
            # 获取所有的记录 {b'3': b'1', b'5': b'2'}
            redis_cart = redis_conn.hgetall('carts_%s' % user.id)
            # 获取字典中所有的key [b'3', b'5']
            redis_sku_ids = redis_cart.keys()
            # 判断用户是否全选
            if selected:  # 全选
                # 将redis_sku_ids列表中的数据解包，添加到set集合中
                redis_conn.sadd('selected_%s' % user.id, *redis_sku_ids)
            else:
                # 取消全选,从set中删除 user_id
                redis_conn.srem('selected_%s' % user.id, *redis_sku_ids)
            # 响应结果
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})

        else:
            # 用户未登录，读取cookie购物车
            cart_str = request.COOKIES.get('carts')

            # 构造响应对象
            response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})

            # 判断购物车是否有数据
            if cart_str:
                # 将cart_str编码后得到 bytes类型字符串
                cart_str_bytes = cart_str.encode()
                # 将 cart_str_bytes进行解码后得到bytes类型字典
                cart_dict_bytes = base64.b64decode(cart_str_bytes)
                # 将cart_dict_bytes转成真正的字典
                cart_dict = pickle.loads(cart_dict_bytes)

                # 遍历所有的购物车记录
                for sku_id in cart_dict:
                    # 每遍历一次，将选择中sku_id进行赋值
                    cart_dict[sku_id]['selected'] = selected  # True / False

                # 将cart_dict转成bytes类型的字典
                cart_dict_bytes = pickle.dumps(cart_dict)
                # 将cart_dict_bytes转成bytes类型的字符串
                cart_str_bytes = base64.b64encode(cart_dict_bytes)
                # 将cart_str_bytes转成字符串
                cookie_cart_str = cart_str_bytes.decode()

                # 重写将购物车数据写入到cookie
                response.set_cookie('carts', cookie_cart_str)

            return response


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
                cart_dict = pickle.loads(cart_dict_bytes)
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

    def get(self,request):
        """查询购物车"""
        # 判断用户是否登录
        user = request.user
        if user.is_authenticated:
            # 用户已登录，查询redis购物车
            redis_conn = get_redis_connection('carts')  # 创建链接到redis的对象

            # 从hash中查询购物车数据 {b'3': b'1'}
            redis_cart = redis_conn.hgetall('carts_%s' % user.id) # hgetall返回的是一个字典
            # 从set中查询购物车选中数据 {b'3'}
            redis_selected = redis_conn.smembers('selected_%s' % user.id)

            """
                未登录用户cookie结构
                {
                    "sku_id1":{
                        "count":"1",
                        "selected":"True"
                    },
                
                }
             """
            cart_dict = {}
            # 将redis_cart和redis_selected进行数据结构的构造，合并数据，数据结构跟未登录用户购物车结构一致
            for sku_id, count in redis_cart.items():
                cart_dict[int(sku_id)] = {
                    "count": int(count), # 在python3中redis存储的数据是bytes,转为int
                    "selected": sku_id in redis_selected
                }
        else:
            # 用户未登录,查询cookies购物车
            cart_str =request.COOKIES.get('carts')
            # 判断cart_str中是否有数据
            if cart_str:
                # 将 cart_str编码成bytes类型的字符串
                cart_str_bytes = cart_str.encode()
                # 将cart_str_bytes解码后得到bytes类型的字典
                cart_dict_bytes = base64.b64decode(cart_str_bytes)
                # 将cart_dict_bytes转成真正的字典
                cart_dict = pickle.loads(cart_dict_bytes)
            else:
                cart_dict = {}

        # 构造响应数据
        sku_ids = cart_dict.keys()  # 获取字典中所有的key,(sku_id)
        skus = SKU.objects.filter(id__in=sku_ids) # 范围查询
        cart_skus = []
        for sku in skus:
            cart_skus.append({
                'id':sku.id,
                'count': cart_dict.get(sku.id).get('count'),
                # 将True，转'True'，方便json解析
                'selected':str(cart_dict.get(sku.id).get('selected')),
                'name':sku.name,
                'default_image_url': sku.default_image.url,
                'price': str(sku.price),
                'amount': str(sku.price * cart_dict.get(sku.id).get('count'))
            })

        # 构造上下文
        context = {
            'cart_skus': cart_skus
        }

        # 响应结果
        return render(request, 'cart.html', context)

    def put(self, request):
        """修改购物车"""
        # 1. 接收参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected', True)

        # 2. 判断参数是否齐全
        if not all([sku_id, count]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 3. 判断sku_id是否存在
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('商品sku_id不存在')
        # 4. 判断count是否为数字
        try:
            count = int(count)
        except Exception:
            return http.HttpResponseForbidden('参数count有误')
        # 5. 判断selected是否为bool值
        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')

        # 6. 判断用户是否登录
        user = request.user
        if user.is_authenticated:
            # 用户已登录，修改redis购物车
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()

            # 由于后端收到的数据是最终的结果，所以"覆盖写入"

            pl.hset('carts_%s' % user.id, sku_id, count)  # 重新写入值到hash表中
            # 修改勾选状态
            if selected:
                pl.sadd('selected_%s' % user.id, sku_id)  # 添加sku_id到set集合中
            else:  # 没有勾选，从set中删除sku_id
                pl.srem('selected_%s' % user.id, sku_id)
            # 执行
            pl.execute()

            # 创建响应对象
            cart_sku = {
                'id': sku_id,
                'count': count,
                'selected': selected,
                'name': sku.name,
                'price': sku.price,
                'amount': sku.price * count,
                'default_image_url': sku.default_image.url
            }

            # 返回响应结果
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '修改购物车成功', 'cart_sku': cart_sku})

        else:
            # 7. 用户未登录，修改cookie购物车
            # 获取cookie中的购物车数据，并且判断是否有购物车数据
            cart_str = request.COOKIES.get('carts')
            if cart_str:  # 购物车有数据，将字符串转成字典
                # 将 cart_str转成bytes类型的字符串
                cart_str_bytes = cart_str.encode()
                # 将cart_str_bytes转成bytes类型的字典
                cart_dict_bytes = base64.b64decode(cart_str_bytes)
                # 将cart_dict_bytes转成真正的字典
                cart_dict = pickle.loads(cart_dict_bytes)
            else: # cookie中没有购物车数据,构造一个空字典
                cart_dict = {}

            # 由于后端收到的是最终的结果，所以"覆盖写入"
            cart_dict[sku_id] = {  # 覆盖购物车中的数据
                'count': count,
                'selected': selected
            }

            # 构造数据结构
            cart_sku = {
                'id': sku_id,
                'count': count,
                'selected': selected,
                'name': sku.name,
                'price': sku.price,
                'amount': sku.price * count,
                'default_image_url': sku.default_image.url
            }

            # 将python字典转为字符串
            # 将cart_dict转成bytes类型的字典
            cart_dict_bytes = pickle.dumps(cart_dict)
            # 将cart_dict_bytes转成bytes类型的字符串
            cart_str_bytes = base64.b64encode(cart_dict_bytes)
            # 将cart_str_bytes转成字符串
            cookie_cart_str = cart_str_bytes.decode()

            # 创建响应对象
            response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'cart_sku': cart_sku})
            # 将新的购物车数据写入到cookie
        response.set_cookie('carts', cookie_cart_str)

        # 9、响应结果
        return response

    def delete(self, request):
        """删除购物车"""
        # 接收参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')

        # 判断sku_id是否存在
        try:
            SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('商品不存在')

        # 判断用户是否登录
        user = request.user
        if user is not None and user.is_authenticated:
            # 用户已登录，删除redis购物车
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()

            # 删除hash购物车商品记录
            pl.hdel('carts_%s' % user.id, sku_id)
            # 同步移除勾选状态
            pl.srem('selected_%s' % user.id, sku_id)
            pl.execute()

            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})
        else:
            # 用户未登录，删除cookie购物车
            # 获取cookie中的购物车数据，并且判断是否有购物车数据
            cart_str = request.COOKIES.get('carts')
            if cart_str: # 有购物车数据，转成字典
                # 将 cart_str转成bytes类型的字符串
                cart_str_bytes = cart_str.encode()
                # 将cart_str_bytes转成bytes类型的字典
                cart_dict_bytes = base64.b64decode(cart_str_bytes)
                # 将cart_dict_bytes转成真正的字典
                cart_dict = pickle.loads(cart_dict_bytes)
            else:
                cart_dict = {}

            # 构造响应对象
            response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})

            # 删除字典指定key所对应的记录
            if sku_id in cart_dict:
                del cart_dict[sku_id] # 如果删除的key不存在，会抛出异常

                # 将cart_dict转成bytes类型的字典
                cart_dict_bytes = pickle.dumps(cart_dict)
                # 将cart_dict_bytes转成bytes类型的字符串
                cart_str_bytes = base64.b64encode(cart_dict_bytes)
                # 将cart_str_bytes转成字符串
                cookie_cart_str = cart_str_bytes.decode()

                # 将删除后的购物车数据到写入新的cookie
                response.set_cookie('carts', cookie_cart_str)

            return response