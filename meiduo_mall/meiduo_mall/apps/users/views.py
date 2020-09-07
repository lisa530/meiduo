import re
from django import http
from django.db import DatabaseError
from django.shortcuts import render,redirect
from django.views import View
from users.models import User
from django.urls import reverse
from django.contrib.auth import login,logout
from django_redis import get_redis_connection
from django.contrib.auth import authenticate

from meiduo_mall.utils.response_code import RETCODE


class LoginView(View):
    """提供用户用登录页面"""

    def get(self, request):
        """
        提供登录界面
        :param request: 请求对象
        :return: 登录界面
        """
        return render(request, 'login.html')

    def post(self,request):
        """用户登录逻辑"""

        # 1. 接收参数
        username = request.POST.get('username')
        password = request.POST.get('password')
        remembered = request.POST.get('remembered')

        # 2.校验参数
        if not all([username,password]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 校验用户名密码是否符合要求
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入正确的用户名')

        if not re.match(r'[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('密码最少8位,最长20位')

        # 3. 认证用户： 使用账号查询用户名是否存在,如果用户名存在,再校验密码
        user = authenticate(username=username,password=password)
        if user is None:
            return render(request, 'login.html',{'account_errmsg':'账号或密码错误'})

        # 4. 状态保持
        login(request,user)
        # 使用remembered确定状态保持周期（实现记住登录）
        if remembered != 'on':
            # 用户没有记录登录：关闭浏览器会话结束
            request.session.set_expiry(0)
        else:
            # 记住了登录： 状态保持为两周：默认是两周
            request.session.set_expiry(None)

        # 重定向到首页
        response = redirect(reverse('contents:index'))
        # 用户名写入到cookie中，过期时间为两周
        # response.set_cookie('key', 'val', 'expiry')
        response.set_cookie('username', user.username,max_age=3600 * 24 * 15)

        # 5. 响应结果
        return response


class LogOutView(View):
    """用户退出登录"""

    def get(self,request):

        # 1.清除状态保持信息
        logout(request)
        # 2.退出登录后重定向到首页
        response = redirect(reverse('contents:index'))
        # 3.删除cookie中的用户名
        response.delete_cookie('username')
        # 响应结果
        return response


class UserInfoView(View):
    """用户中心"""

    def get(self,request):
        """提供用户中心页页"""
        return render(request, 'user_center_info.html')


class RegisterView(View):
    """用户注册"""

    def get(self,request):
        """提供用户注册页面"""
        return render(request,'register.html')

    def post(self,request):
        """实现用户注册业务逻辑"""
        # 1. 接收前端表单数据
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('mobile')
        sms_code_client = request.POST.get('sms_code')
        allow = request.POST.get('allow')

        # 2.校验参数
        # 判断参数是否齐全：all([列表])
        if not all([username,password,password2,mobile,all]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 判断用户名是否合法
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入5-20个字符的用户名')
        # 判断密码是否为8-20个数字
        if not re.match(r'^[a-zA-Z0-9-_]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')
        # 确认两次密码是否一致
        if password != password2:
            return http.HttpResponseForbidden('两次密码输入不一致')
        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('请输入正确的手机号')

        # 判断短信验证码是否输入正确
        redis_conn = get_redis_connection('verify_code')
        # 从redis连接对象中获取短信验证码
        sms_code_server = redis_conn.get('sms_%s' % mobile)
        # 短信验证码过期,返回提示信息
        if sms_code_server is None:
            return render(request, 'regsiter.html',{'sms_code_errmsg': '短信验证码已失效'})
        # 判断用户输入的和redis中存储的短信验码是否相同
        if sms_code_client != sms_code_server.decode(): # 将bytes转成str
            return render(request, 'register.html', {'sms_code_errmsg': '输入短信验证码有误'})

        # 判断是否勾选用户协议
        if allow != 'on':
            return http.HttpResponseForbidden('请勾选用户协议')

        # 3.保存注册数据
        try:
            user = User.objects.create_user(username=username,password=password,mobile=mobile)
        except DatabaseError:
            return render(request, 'register.html', {'register_errmsg': '注册失败'})

        # 4. 实现状态操持写入session
        login(request,user)

        # 5.响应结果：重定向到首页
        # return http.HttpResponse('注册成功,重定向到首页')

        # return redirect('/')
        # 使用reverse反向解析：
        # reverse('contents:index') == '/'
        return redirect(reverse('contents:index'))


class UsernameCountView(View):
    """用户名重复注册"""

    def get(self,request,username):
        """

        :param request: 请求对象
        :param username: 用户名
        :return:
        """

        # 1.使用username查询出数据库中对应记录
        count = User.objects.filter(username=username).count()
        # 2. 返回结果数据
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': RETCODE.OK, 'count': count})


class MobileCountView(View):
    """判断手机号是否重复注册"""

    def get(self,request,mobile):

        # 1.查询数据库该手机号记录是否存在
        count = User.objects.filter(mobile=mobile).count()
        # 2. 返回响应
        return http.JsonResponse({'code': RETCODE.OK, 'error_msg': RETCODE.OK, 'count': count})



