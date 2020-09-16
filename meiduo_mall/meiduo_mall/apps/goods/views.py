from django.shortcuts import render
from django.views import View
from django import http
from django.core.paginator import Paginator,EmptyPage
from django.utils import timezone
from datetime import datetime

from goods.models import GoodsCategory,SKU,GoodsVisitCount
from contents.utils import get_categories
from .utils import get_breadcrumb
from . import constants
from meiduo_mall.utils.response_code import RETCODE


class DetailVisitView(View):
    """统计分类商品的访问量"""

    def post(self, request, category_id):
        # 接收参数和校验参数
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseForbidden('category_id 不存在')

        # 获取当天的日期
        t = timezone.localtime()
        # 获取当天的时间字符串
        today_str = '%d-%02d-%02d' % (t.year, t.month, t.day)
        # 将当天的时间字符串转成时间对象datetime，为了跟date字段的类型匹配 2019:05:23  2019-05-23
        today_date = datetime.strptime(today_str, '%Y-%m-%d') # 时间字符串转时间对象；datetime.strftime() # 时间对象转时间字符串

        # 判断当天中指定的分类商品对应的记录是否存在
        try:
            # 使用当前的日期和当前的分类作为条件，查询记录是否存在
            counts_data = GoodsVisitCount.objects.get(date=today_date, category=category)
        except GoodsVisitCount.DoesNotExist:
            # 如果不存在，直接创建记录对应的对象
            counts_data = GoodsVisitCount()

        # 记录存在，为指定的分类商品的记录赋值
        try:
            counts_data.category = category
            counts_data.count += 1
            counts_data.date = today_date
            counts_data.save()
        except Exception as e:
            return http.HttpResponseServerError('统计失败')

        # 响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


class DetailView(View):
    """商品详情页"""

    def get(self,request,sku_id):
        """提供商品详情页"""
        # 1.接收和校验参数
        try:
            # 查询sku是否合法
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            # return http.HttpResponseNotFound('sku_id不存在')
            return render(request, '404.html')

        # 2. 获取商品分类
        categories = get_categories()

        # 3. 获取商品面包屑导航（接收一个category类别)
        breadcrumb = get_breadcrumb(sku.category) # 多查一： 通过sku对象.外键查询出 sku商品所属性类别

        # 获取当前商品的规格，按规格的id进行排序
        sku_specs = sku.specs.order_by('spec_id') # 一查多：一类模型类.related_name，通过sku.specs得到商品的规格信息
        sku_key = []
        # 遍历所有的商品规格
        for spec in sku_specs:
            # 将规格对应的选项id追加到列表中
            sku_key.append(spec.option.id)  # 多查一： 多类模型类.外键

        # 获取当前商品的所有SKU
        skus = sku.spu.sku_set.all()
        # 构建不同规格参数（选项）的sku字典
        spec_sku_map = {}
        for s in skus:
            # 获取sku的规格信息,按规格id排序
            s_specs = s.specs.order_by('spec_id') # 一查多：一类模型类.related_name
            # 用于形成规格参数sku字典的键
            key = []
            for spec in sku_specs:
                key.append(spec.option.id) # 将规格选项信息添加到列表中
                # 向规格参数-sku字典添加记录
                spec_sku_map[tuple(key)] = s.id
            # 获取当前商品的规格信息
            goods_specs = sku.spu.specs.order_by('id')
            # 若当前sku的规格信息不完整，则不再继续
            if len(sku_key) < len(goods_specs):
                return
            # 遍历当前sku规格信息，得到key和值
            for index, spec in enumerate(goods_specs):
                # 复制当前sku的规格键
                key = sku_key[:]
                # 查询所有规格选项信息
                spec_options = spec.options.all()
                # 遍历规格选项信息
                for option in spec_options:
                    # 将规格选项id赋值给 sku规格键
                    key[index] = option.id
                    option.sku_id = spec_sku_map.get(tuple(key))
                spec.spec_options = spec_options

        # 4. 构造上下文
        context = {
            'categories': categories, # 商品分类
            'breadcrumb': breadcrumb, # 面包屑导航
            'sku': sku, # sku商品
            'specs': goods_specs
        }

        # 5. 响应结果
        return render(request,'detail.html', context)


class HotGoodsView(View):
    """商品热销排行"""

    def get(self,request,category_id):
        """获取商品热销排行逻辑"""
        skus = SKU.objects.filter(category_id=category_id, is_launched=True).order_by('-sales')[:2]
        # 将模型类列表转成字典，构造json数据
        hot_skus = []
        for sku in skus:
            sku_dict = {
                'id': sku.id,
                'name':sku.name,
                'default_image_url':sku.default_image.url, # 一定要取全路径
                'price': sku.price
            }
            hot_skus.append(sku_dict)

        # 返回json数据
        return http.JsonResponse({'code': RETCODE.OK,'errmsg':'OK', 'hot_skus': hot_skus})


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
        paginator = Paginator(skus,constants.GOODS_LIST_LIMIT) # 把skus进行分页，每页显示5条记录
        try:
            page_skus = paginator.page(page_num) # 获取当用户查看的页数（分页后的数据)
        except EmptyPage: # page_num有误，返回404
            return http.HttpResponseNotFound('Empty Page')
        total_page = paginator.num_pages # 获取总页数

        # 构造上下文
        context = {
            'categories': categories, # 商品分类
            'breadcrumb': breadcrumb, # 面包屑导航
            'page_skus': page_skus, # 要分页的数据
            'total_page': total_page, # 总页数
            'page_num': page_num, # 所在页
            'category_id': category_id, # 三级分类id
            'sort': sort  # 排序字段
        }
        # 响应结果
        return render(request,'list.html', context)