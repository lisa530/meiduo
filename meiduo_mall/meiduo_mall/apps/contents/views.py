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
            # 构造基本数据结构： 只有11个组
            """
           {
            "1":{
                "channels":[  # 所有的一级分类
                    {"id":1, "name":"手机", "url":"http://shouji.jd.com/"},      
                ],
                "sub_cats":[  # 二级分类
                    {
                        "id":38, 
                        "name":"手机通讯", 
                        "sub_cats":[
                            {"id":115, "name":"手机"},              
                        ]
                    },
           """
            # 判断group_id是否在categorie字典中
            if group_id not in categories:
                categories[group_id] = {'channels': [],'sub_cats':[]}

            # 3.查询出当前频道对应的一级类别
            cat1 = channel.category # 多查一：多类模型类.外键
            # 将cat1添加到channels(一级分类添加到频道组中)
            categories[group_id]['channels'].append({
                'id':cat1.id, # 一级分类id
                'name':cat1.name, # 一级分类名字
                'url': channel.url # 频道的地址
            })

            # 4.查询二级和三级类别
            for cat2 in cat1.subs.all(): # 通过一级类别查询出二级类别
                # 查询遍历三级类别
                cat2.sub_cats = [] # 给二级类别添加一个保存三级类加别列表
                for cat3 in cat2.subs.all(): # 从二级类别查询三级
                    cat2.sub_cats.append(cat3) # 将三级类别添加到二级sub_cats

                # 将二级类添加到一级类别的sub_cats
                categories[group_id]['sub_cats'].append(cat2)

        # 构造上下文
        context = {
            'categories':categories
        }

        # 返回渲染后的数据
        return render(request,'index.html', context)
