import base64,pickle
from django_redis import get_redis_connection


def merge_carts_cookies_redis(request, user, response):
    """合并购物车"""

    # 获取cookies中的购物车数据
    cart_str = request.COOKIES.get('carts')

    # 判断cookies中的购物车数据是否存在
    if not cart_str:
        return response

    # 将 cart_str转成bytes类型的字符串
    cookie_cart_str_bytes = cart_str.encode()
    # 将cart_str_bytes转成bytes类型的字典
    cookie_cart_dict_bytes = base64.b64decode(cookie_cart_str_bytes)
    # 将cart_dict_bytes转成真正的字典
    cookie_cart_dict = pickle.loads(cookie_cart_dict_bytes)

    """
        {
            "sku_id1":{
                "count":"1",
                "selected":"True"
            },
            "sku_id3":{
                "count":"3",
                "selected":"False"
            }
        }
        """

    # 准备新的数据容器：保存新的sku_id:count、selected、unselected
    new_cart_dict = {} # 保存sku_id字典对应count的值
    new_selected_add = [] # 保存全选的sku_id字典中selected键对应的值True
    new_selected_rem = [] # 保存未全选的sku_id字典中selected键对应的值Flase

    # 遍历出cookies中的购物车数据
    for sku_id, cookie_dict in cookie_cart_dict.items(): # 得到字典的key和vlaue
        # 正确的数据结构
        new_cart_dict[sku_id] = cookie_dict['count'] # 取出sku_id对应的值count 并赋值给count

        if cookie_dict['selected']:  # 选中状态， 将sku_id添加到新的字典中
            new_selected_add.append(sku_id)
        else:  # 未全选， 将sku_id添加到 new_selected_rem列表中
            new_selected_rem.append(sku_id)

    # 根据新的数据结构，合并到redis
    redis_conn = get_redis_connection('carts')
    pl = redis_conn.pipeline()

    # 将new_cart_dict字典中保存的sku_id字典中count值 保存在redis中
    pl.hmset('carts_%s' % user.id, new_cart_dict)  # 操作hash表，hmset设置多个值
    if new_selected_add:  # 全选状态
        # 全选状态的selected为True添加到set中
        pl.sadd('selected_%s' % user.id, *new_selected_add)
    if new_selected_rem:  # 未全选
        # 将selected为False的购物车数据，从set中删除
        pl.srem('selected_%s' % user.id, *new_selected_rem)

    # 执行
    pl.execute()