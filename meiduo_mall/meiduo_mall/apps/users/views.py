import re
from django import http
from django.db import DatabaseError
from django.shortcuts import render,redirect
from django.views import View
from users.models import User
from django.urls import reverse
from django.contrib.auth import login


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