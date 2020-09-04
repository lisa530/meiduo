from django.shortcuts import render
from django.views import View
from verifications.libs.captcha.captcha import  captcha
from django_redis import get_redis_connection
from django import http
from . import constants


class ImageCodeView(View):
    """图形验证码"""
    def get(self, request, uuid):
        """

        :param request:  请求对象
        :param uuid: 通用唯一识别码，用于唯一标识该图形验证码属于哪个用户的
        :return: 数据类型 image/jpg
        """
        # 1.生成图片验证码
        text, image = captcha.generate_captcha()
        # 2. 保存图片验证码
        # 获取redis连接对象
        redis_conn = get_redis_connection('verify_code')
        # 使用redis_conn.setex('key'  'expires', 'value')
        redis_conn.setex('img_%s' % uuid, constants.IMAGE_CODE__REDIS_EXPIRES, text)
        # 3 响应图片验证码
        return http.HttpResponse(image, content_type='image/jpg')



