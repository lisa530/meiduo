from django.shortcuts import render
from django.views import View
from .models import Area
from meiduo_mall.utils.response_code import RETCODE
from django import http
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

                    # 响应省级Json数据
                return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'province_list':province_list})
            except Exception as e:
                logger.error(e)
                return http.JsonResponse({'code':RETCODE.DBERR, 'errmsg': '查询省份数据错误'})
        else:
            pass