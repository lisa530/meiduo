from django.shortcuts import render,redirect
from django.views import View
from QQLoginTool.QQtool import OAuthQQ
from .models import OAuthQQUser
from django.conf import settings
from django import http
from django.contrib.auth import login

from meiduo_mall.utils.response_code import RETCODE
import logging
from .utils import generate_access_token


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
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID, client_secret=settings.QQ_CLIENT_SECRET,
                            redirect_uri=settings.QQ_REDIRECT_URI)

        try:
            # 使用code获取access_token
            access_token = oauth.get_access_token(code)
            # 使用access_token获取openid
            openid = oauth.get_open_id(access_token)
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError('OAuth2.0认证失败')

        # 3.使用openid判断该QQ用户是否绑定过美多商城的用户
        try:
            oauth_user = OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist:

            # openid未绑定过美多商城用户
            access_token_openid = generate_access_token(openid)
            context = {'access_token_openid': access_token_openid}
            # 将加密后的openid进行渲染返回
            return render(request, 'oauth_callback.html',context)
        else:
            # openid绑定过美多商城用户：oauth_user.user表示从QQ登陆模型类对象中找到关联的用户模型类对象
            login(request,oauth_user.user)
            # 提取state参数
            next = request.GET.get('state')
            # 重定向到state:从哪来，QQ登录完之后回哪而去
            response = redirect(next)
            # 将用户名写入到 cookie中， 有效期为15天
            response.set_cookie('username', oauth_user.user.username, max_age=3600 * 24 * 15)

            # 响应QQ登录结果
            return response



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
