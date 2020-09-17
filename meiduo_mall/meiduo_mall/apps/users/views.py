import re,json,logging
from django import http
from django.db import DatabaseError
from django.shortcuts import render,redirect
from django.views import View
from users.models import User,Address
from django.urls import reverse
from django.contrib.auth import login,logout
from django_redis import get_redis_connection
from django.contrib.auth import authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from goods.models import SKU

from meiduo_mall.utils.response_code import RETCODE
from meiduo_mall.utils.views import LoginRequiredJSONMixin
from celery_tasks.email.tasks import send_verify_email
from . utils import generate_verify_email_url,check_verify_email_token
from . import constants
from carts.utils import merge_carts_cookies_redis



# 创建日志输出器
logger = logging.getLogger('django')


class UserBrowseHistory(LoginRequiredJSONMixin,View):
    """用户浏览记录"""

    def post(self,request):
        """保存用户商品浏览记录"""
        # 接收参数
        json_str = request.body.decode()
        json_dict = json.loads(json_str)
        sku_id = json_dict.get('sku_id')

        # 校验参数
        try:
            SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('参数sku_id错误')

        # 保存sku_id到redis
        redis_conn = get_redis_connection('history')
        user = request.user
        pl = redis_conn.pipeline()
        # 先去重
        pl.lrem('history_%s' % user.id, 0, sku_id)
        # 再保存：最近浏览的商品在最前面
        pl.lpush('history_%s' % user.id, sku_id)
        # 最后截取
        pl.ltrim('history_%s' % user.id, 0, 4)
        #执行
        pl.execute()

        # 响应结果
        return http.JsonResponse({'code': RETCODE.OK,'errmsg':'OK'})

    def get(self, request):
        """查询用户商品浏览记录"""
        # 获取登录用户信息
        user = request.user
        # 创建连接到redis对象
        redis_conn = get_redis_connection('history')
        # 取出列表数据（核心代码）
        sku_ids = redis_conn.lrange('history_%s' % user.id, 0, -1)  # (0, 4)

        # 将模型转字典
        skus = []
        for sku_id in sku_ids:
            sku = SKU.objects.get(id=sku_id)
            skus.append({
                'id': sku.id,
                'name': sku.name,
                'price': sku.price,
                'default_image_url': sku.default_image.url
            })

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'skus': skus})


class ChangePasswordView(LoginRequiredMixin, View):
    """修改密码"""

    def get(self, request):
        """展示修改密码界面"""
        return render(request, 'user_center_pass.html')

    def post(self, request):
        """实现修改密码逻辑"""

        # 1.接收参数
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        new_password2 = request.POST.get('new_password2')

        # 2. 校验参数
        if not all([old_password, new_password, new_password2]):
            return http.HttpResponseForbidden('缺少必传参数')
        try:
            request.user.check_password(old_password)  # 检查旧密码是否正确
        except Exception as e:
            logger.error(e)
            return render(request, 'user_center_pass.html', {'origin_pwd_errmsg': '原始密码错误'})

        if not re.match(r'^[0-9A-Za-z]{8,20}$', new_password):
            return http.HttpResponseForbidden('密码最少8位，最长20位')
        if new_password != new_password2:  # 判断新密码和确认密码是否一致
            return http.HttpResponseForbidden('两次输入的密码不一致')

        # 3. 修改密码
        try:
            request.user.set_password(new_password)  # 设置新密码
            request.user.save()  # 保存密码
        except Exception as e:
            logger.error(e)
            return render(request, 'user_center_pass.html', {'change_pwd_errmsg': '修改密码失败'})

        # 4.清理状态保持信息
        logout(request)  # 退出登录
        response = redirect(reverse('users:login'))  # 重定向到登录页面
        response.delete_cookie('username')  # 从cookie中删除用户信息

        # 5. 响应密码修改结果：重定向到登录界面
        return response


class UpdateTitleAddressView(LoginRequiredJSONMixin, View):
    """更新地址标题"""

    def put(self,request, address_id):
        """实现更新地址标题逻辑"""
        # 1. 接收参数：title
        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')
        # 2. 校验参数
        if not title:
            return http.HttpResponseForbidden('缺少title')

        try:
            # 3. 查询当前要更新的标题的地址
            address = Address.objects.get(id=address_id)
            # 将新的地址标题覆盖原有地址标题
            address.title = title
            address.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '更新标题失败'})

        # 4. 响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '更新标题成功'})


class DefaultAddressView(LoginRequiredJSONMixin, View):
    """设置默认收货地址"""

    def put(self,request, address_id):
        """实现设置默认地址"""
        # 1. 查询出哪个地址作为登录用户的默认地址
        try:
            address = Address.objects.get(id=address_id)
            # 将指定的地址设置为当前登录用户的默认地址
            request.user.default_address = address
            request.user.save()

        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '设置默认地址失败'})

        # 返回响应数据
        return  http.JsonResponse({'code':RETCODE.OK, 'errmsg': '设置默认地址成功'})


class UpdateDestoryAddressView(LoginRequiredJSONMixin, View):
    """更新和删除地址"""

    def put(self,request, address_id):
        """更新地址"""

        # 1. 接收和校验参数
        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 校验参数
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')

        # 2.使用最新的地址信息覆盖指定的旧的地址信息
        try:
            Address.objects.filter(id=address_id).update(
                user=request.user,
                title = receiver,
                receiver = receiver,
                province_id=province_id,
                city_id = city_id,
                tel=tel,
                mobile=mobile,
                email=email,
                place=place
            )
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '修改地址失败'})

        # 将要更新的地址转成字典数据
        address = Address.objects.get(id=address_id) # 查询要更新的收货地址
        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }

        # 3.响应新的地址信息给前端渲染
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg':'修改地址成功', 'address': address_dict})

    def delete(self,request, address_id):
        """删除指定收货地址"""
        # 实现指定地址的逻辑删除：is_delete=True
        try:
            # 查询当前要删除的地址
            address = Address.objects.get(id=address_id)
            address.is_deleted = True # 修改is_deleted的值
            address.save() # 保存

        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code':RETCODE.DBERR, 'errmsg': '删除地址失败'})
        # 响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '删除地址成功'})


class AddressCreateView(LoginRequiredJSONMixin,View):
    """新增用户地址"""

    def post(self, reqeust):
        """实现新增地址逻辑"""

        # 判断用户地址数量是否超过上限：查询当前登录用户的地址数量
        # count = Address.objects.filter(user=reqeust.user).count()
        count = reqeust.user.addresses.count()  # 一查多，使用related_name查询
        if count > constants.USER_ADDRESS_COUNTS_LIMIT:
            return http.JsonResponse({'code': RETCODE.THROTTLINGERR, 'errmsg': '超出用户地址上限'})

        # 接收参数
        json_str = reqeust.body.decode()
        json_dict = json.loads(json_str)
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 校验参数
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')

        # 保存用户传入的地址信息
        try:
            address = Address.objects.create(
                user=reqeust.user,
                title=receiver,  # 标题默认就是收货人
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email,
            )

            # 如果登录用户没有默认的地址，我们需要指定默认地址
            if not reqeust.user.default_address:
                reqeust.user.default_address = address
                reqeust.user.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '新增地址失败'})

        # 构造新增地址字典数据
        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }

        # 响应新增地址结果：需要将新增的地址返回给前端渲染
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '新增地址成功', 'address': address_dict})


class AddressView(LoginRequiredMixin,View):
    """展示收货地址"""

    def get(self,request):
        """查询并展示用户收货地址"""

        # 1.获取当前登录用户对象
        login_user = request.user
        # 2.使用当前登录对象和is_delete=False 作为查询条件
        addresses = Address.objects.filter(user=login_user, is_deleted=False)
        # 3. 将用户地址模型类列表 转为 字典列表：
        address_list = []
        for address in addresses:
            address_dict = {
                "id": address.id,
                "title": address.title,
                "receiver": address.receiver,
                "province": address.province.name, # 省名称
                "citry": address.city.name, # 市名称
                "district": address.district.name, # 区或县名称
                "place": address.place,
                "mobile": address.mobile,
                "tel": address.tel,
                "email": address.email
            }
            address_list.append(address_dict)

        # 因为JsonResponse和Vue.js不认识模型类型，只有Django和Jinja2模板引擎认识
        # 构造模板上下文

        context = {
            # 'default_address_id': login_user.default_address_id, # 从当前登录用户中取出默认收货地址id
            'default_address_id': login_user.default_address_id or '0',
            'addresses': address_list
        }

        # 4. 响应Json数据
        return render(request,'user_center_site.html',context)


class VerifyEmailView(View):
    """验证邮件链接"""
    def get(self,request):
        # 1.接收参数和校验参数
        token = request.GET.get('token')
        if not token:
            return http.HttpResponseForbidden('缺少token')
        # 3. 从token中提取用户的信息(user_id)
        user = check_verify_email_token(token)
        if not user:
            return http.HttpResponseBadRequest('无效的token')
        # 将用户的email_active字段设置为True
        try:
            user.email_active = True
            user.save()
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError('激活邮件失败')
        # 返回邮箱验证结果： 重定向到用户中心
        return  redirect(reverse('users:info'))


class EmailView(View):
    """添加邮箱"""

    def put(self,request):
        # 1. 接收参数,非表单请求体数据，通过request.body
        json_str = request.body.decode()
        json_dict = json.loads(json_str)
        email = json_dict.get('email')

        # 2.校验参数
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return http.HttpResponseForbidden('参数email有误')

        # 3. 将用户输入传用度的邮箱保存到用户数据库的email字段中
        try:
            request.user.email = email # request.user当前登录的对象绑定emial字段
            request.user.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg':'添加邮箱失败'})

        # 4. 调用加密后的验证邮件链接方法
        verify_url = generate_verify_email_url(request.user) # 从当前登录用户中取出user
        # 使用celery发送邮件
        send_verify_email.delay(email, verify_url) # 接收邮件地址，验证邮件链接

        # 响应结果
        return http.JsonResponse({'code':RETCODE.OK ,'errmsg': 'OK'})


class UserInfoView(LoginRequiredMixin,View):
    """用户中心"""

    def get(self,request):
        """提供用户中心页面"""
        # 定义模板上下文数据
        # 如果loginRequiredMixin判断出用户已登录， 那么request.user就是当前登录用户
        context = {
            'username': request.user.username,
            'mobile': request.user.mobile,
            'email': request.user.email,
            'email_active': request.user.email_active
        }
        # 返回渲染的的数据
        return render(request, 'user_center_info.html', context)


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

        # 先取出next查询字符串
        next = request.GET.get('next')
        # 判断 next是否存在
        if next:
            # 重定向到next
            response = redirect(next)
        else:
            # 重定向到首页
            response = redirect(reverse('contents:index'))
        # 用户名写入到cookie中，过期时间为两周
        # response.set_cookie('key', 'val', 'expiry')
        response.set_cookie('username', user.username,max_age=3600 * 24 * 15)
        # 用户登录成功，合并cookie购物车到redis购物车
        response = merge_carts_cookies_redis(request=request, user=user, response=response)

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



