from django.shortcuts import render
from django.views import View
from .models import Area
from meiduo_mall.utils.response_code import RETCODE
from django import http
from django.core.cache import cache

import logging


# Create your views here.

# 创建日志输出器
logger = logging.getLogger('django')


class AreasView(View):
    """查询省市区数据"""

    def get(self,request):
        # 接收参数
        area_id = request.GET.get('area_id')
        # 判断当前要查询省份数据还是市区数据
        if not area_id:
            # 获取并判断是否有缓存
            province_list = cache.get('province_list')
            # 缓存中没有数据
            if not province_list:
                #  查询省级数据
                try:
                    province_model_list = Area.objects.filter(parent_id__isnull=True)

                    # 将模型列表 转成 字典列表
                    province_list = []
                    # 遍历模型列表，取出每一个模型列表
                    for province_model in province_model_list:
                        # 将每个模型数据封装在一个字典中
                        province_dict = {
                            'id': province_model.id,
                            'name': province_model.name
                        }
                        # 将字典添加到列表中
                        province_list.append(province_dict)

                    # 缓存省份字典列表数据:默认存储到redis中别名为"default"的配置中
                    cache.set('province_list', province_list, 3600)

                except Exception as e:
                    logger.error(e)
                    return http.JsonResponse({'code':RETCODE.DBERR, 'errmsg': '查询省份数据错误'})

            # 响应省级Json数据
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'province_list': province_list})
        else:

            sub_data = cache.get('sub_area_' + area_id) # 获取缓存
            # 判断是否有缓存
            if not sub_data:
                # 查询城市或区县数据
                try:
                    # 根据area_id查询，如果area_id是省级id，那么查询的是市级数据
                    parent_model = Area.objects.get(id=area_id)
                    # 一查多： 一类对象.related_name属性的值
                    sub_model_list = parent_model.subs.all()

                    # 将子级模型转成列表
                    subs = []
                    for sub_model in sub_model_list:
                        sub_dict ={
                           'id': sub_model.id, # 子级id
                           'name':sub_model.name # 子级名称
                        }
                        subs.append(sub_dict)
                        # 构造子级 json数据格式
                        sub_data = {
                            'id':parent_model.id, # 省级id
                            'name': sub_model.name, # 省级名称
                            'subs': subs # 子级列表
                        }
                    # 缓存城市或者区县数据
                    # cache.set(key, value(城市id, 子级，过期时间:10分钟)
                    cache.set('sub_data_' + area_id, sub_data, 3600)
                except Exception as e:
                    logger.error(e)
                    return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '查询城市或区县数据错误'})

            # 响应城市或区县JSON数据
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'sub_data': sub_data})