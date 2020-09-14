from django.shortcuts import render
from django.views import View
from django import http
from django.core.paginator import Paginator,EmptyPage

from goods.models import GoodsCategory
from contents.utils import get_categories
from .utils import get_breadcrumb


class ListView(View):
    """商品列表页"""

    def get(self,request, category_id,page_num):
        """查询并渲染商品列表页"""
        # 校验参数category_id的范围
        try:
            # 三级类别
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseForbidden('参数category_id不存在')

        # 获取sort参数：如果sort没有值，取'default'
        sort = request.GET.get('sort','default')
        # 根据sort选择排序字段，排序字段必须是模型类的属性
        if sort == 'price':
            sort_field = 'price' # 按照价格由低到高排序
        elif sort == 'hot':
            sort_field = '-sales' # 按照销量由高到低排序
        else:
            # 只要不是'price'和'-sales'其他的所有情况都归为'default'
            sort = 'default'
            sort_field = 'create_time' # 当出现?sort=itcast 也把sort设置我'default'
        # 查询首页商品分类
        categories = get_categories()

        # 查询面包屑导航：一级/二级/三级
        breadcrumb = get_breadcrumb(category)
        # 分页和排序查询： category查询sku 一查多：一类模型对象.多类模型类名小写_set.filter
        # 查询商品已上架 并按字段进行排序
        skus = category.sku_set.filter(is_launched=True).order_by(sort_field)

        # 创建分页器
        # Paginator('要分页的记录', '每页记录的条数')
        paginator = Paginator(skus, 5) # 把skus进行分页，每页显示5条记录
        try:
            page_skus = paginator.page(page_num) # 获取当用户当查看的页数
        except EmptyPage: # page_num有误，返回404
            return http.HttpResponseNotFound('Empty Page')
        total_page = paginator.num_pages # 获取总页数

        # 构造上下文
        context = {
            'categories': categories,
            'breadcrumb': breadcrumb,
        }
        # 响应结果
        return render(request,'list.html', context)