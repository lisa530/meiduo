from django.shortcuts import render
from django.views import View
from QQLoginTool.QQtool import OAuthQQ
from django.conf import settings
from django import http

from meiduo_mall.utils.response_code import RETCODE
import logging


# 创建日志输出器
logger = logging.getLogger('django')


class QQAuthUserView(View):
    """处理QQ登录回调地址 oauth_callback"""

    def get(self,request):
        """处理QQ登录回调的业务逻辑"""

        # 1.获取code参数
        code = request.GET.get('code')
        if not code:
            return http.HttpResponseForbidden('获取code失败')

        # 2.创建工具对象
        oauth = oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID, client_secret=settings.QQ_CLIENT_SECRET,
                            redirect_uri=settings.QQ_REDIRECT_URI)

        try:
            # 使用code获取access_token
            access_token = oauth.get_access_token(code)
            # 使用access_token获取openid
            openid = oauth.get_open_id(access_token)
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError('OAuth2.0认证失败')
        pass


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
