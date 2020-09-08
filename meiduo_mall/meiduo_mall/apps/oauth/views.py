from django.shortcuts import render
from django.views import View
from QQLoginTool.QQtool import OAuthQQ
from django.conf import settings
from django import http

from meiduo_mall.utils.response_code import RETCODE

# Create your views here.

class QQAuthURLView(View):
    """提供QQ扫码登录页面"""

    def get(self,request):
        # 1. 接收next参数
        code = request.GET.get('next')
        # 2创建工具对象
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID, client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI)
        # 生成QQ登录扫码链接地址
        login_url = oauth.get_qq_url()
        # 3.响应结果
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': 'OK',
            'login_url':login_url
        })
