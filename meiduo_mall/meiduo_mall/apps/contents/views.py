from django.shortcuts import render
from django.views import View

from goods.models import GoodsChannelGroup,GoodsCategory,GoodsChannel
from collections import OrderedDict

class IndexView(View):
    """首页广告"""

    def get(self,request):
        """查询首页广告页面"""
        # 定义商品分类字典
        categories = OrderedDict()
        # 1. 查询所有的频道: 37个一级类别
        # 按group_id和sequence排序
        channels = GoodsChannel.objects.order_by('group_id', 'sequence')
        # 2.遍历所有频道
        for channel in channels:
            # 获取当前频道所在组
            group_id = channel.group_id # 多查一：一类模型类.外键字段
            # 构造基本数据结构：
            """
               {
                   "group_id":{
                       "channels":[],
                   "sub_cats":[]

                   },
               }
           """
            # 判断group_id是否在categorie字典中
            if group_id not in categories:
                categories[group_id] = {'channels': [],'sub_cats':[]}

            # 查询出当前频道对应的一级类别
            cat1 = channel.category # 多查一：多类模型类.外键
            # 将cat1添加到channels(一级分类添加到频道组中)
            categories[group_id]['channels'].append({
                'id':cat1.id,
                'name':cat1.name,
                'url': channel.url
            })

            return render(request,'index.html')
