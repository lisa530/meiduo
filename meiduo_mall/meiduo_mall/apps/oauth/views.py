from django.shortcuts import render,redirect
from django.views import View
from QQLoginTool.QQtool import OAuthQQ
from .models import OAuthQQUser
from django.conf import settings
from django import http
from django.contrib.auth import login
from django_redis import get_redis_connection
from users.models import User

from meiduo_mall.utils.response_code import RETCODE
import logging,re
from .utils import generate_access_token,check_access_token


# 创建日志输出器
logger = logging.getLogger('django')


class QQAuthUserView(View):
    """处理QQ登录回调地址 oauth_callback"""

    def get(self,request):
        """处理QQ登录回调的业务逻辑"""

        # 1.获取code参数
        code = request.GET.get('code')
        # state = request.GET.get('state','/')
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

            # 重定向到state:从哪来，QQ登录完之后回哪而去
            next = request.GET.get('state')
            response = redirect(next)
            # 将用户名写入到 cookie中， 有效期为15天
            response.set_cookie('username', oauth_user.user.username, max_age=3600 * 24 * 15)

            # 响应QQ登录结果
            return response

    def post(self, request):
        """实现绑定用户的逻辑"""
        # 1. 接收参数
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        sms_code_client = request.POST.get('sms_code')
        access_token_openid = request.POST.get('access_token_openid')

        # 接收重定向地址
        # state = request.GET.get('state', '/')

        # 2. 校验参数
        # 判断参数是否齐全
        if not all([mobile, password, sms_code_client]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('请输入正确的手机号码')
        # 判断密码是否合格
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')
        # 判断短信验证码是否一致
        redis_conn = get_redis_connection('verify_code')
        sms_code_server = redis_conn.get('sms_%s' % mobile)
        if sms_code_server is None:
            return render(request, 'oauth_callback.html', {'sms_code_errmsg': '无效的短信验证码'})
        if sms_code_client != sms_code_server.decode():
            return render(request, 'oauth_callback.html', {'sms_code_errmsg': '输入短信验证码有误'})

        # 3. 判断openid是否有效：openid使用itsdangerous签名之后只有600秒的有效期
        openid = check_access_token(access_token_openid)
        if not openid:
            return render(request, 'oauth_callback.html', {'openid_errmsg': 'openid已失效'})

        # 4. 保存注册数据
        try:
            # 4.1 使用手机号查询对应的用户是否存在
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            # 4.2 如果手机号用户不存在,使用手机号作为用户名,新建用户
            user = User.objects.create_user(username=mobile, password=password,mobile=mobile)
        else:
            # 4.3 用户存在, 校验密码
            if not user.check_password(password):
                return render(request, 'oauth_callback.html', {'account': '账号或密码错误'})

        # 5. 将新建用户和已存在用户和 openid绑定到一起
        # create封装了创建模型类对象和保存对象方法
        try:
            oauth_qq_user = OAuthQQUser.objects.create(user=user, openid=openid)
        except Exception as e:
            logger.error(e)  # 输出错误信息到日志中
            return render(request, 'oauth_callback.html', {'qq_login_errmsg': '账号或密码错误'})

        # 6. 实现状态保持
        login(request, oauth_qq_user.user)

        # 7.响应绑定结果
        next = request.GET.get('state')  # 从查询字符串中取出state所在地址
        # 重定向state, state从哪来，QQ登录完之后回哪而去
        response = redirect(next)
        # 登录时用户名写入到cookie,有效期15天
        response.set_cookie('username', oauth_qq_user.user.username, max_age=3600 * 24 * 15)

        return response


class QQAuthURLView(View):
    """提供QQ扫码登录页面"""

    def get(self,request):
        # 1. 接收next参数
        # next表示从哪个页面进入到的登录页面，将来登录成功后，就自动回到那个页面
        next = request.GET.get('next')
        # 2创建工具对象
        oauth = OAuthQQ(
            settings.QQ_CLIENT_ID,
            settings.QQ_CLIENT_SECRET,
            settings.QQ_REDIRECT_URI,
            next
        )
        # 生成QQ登录扫码链接地址
        login_url = oauth.get_qq_url()

        # 3.响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'login_url': login_url})



