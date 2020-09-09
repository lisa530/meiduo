from django.contrib.auth.backends import ModelBackend
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadData
import re
from .models import User
from django.conf import settings
from . import  constants


def check_verify_email_token(token):
    """
        反序列化token,获取到user
        :param token: 序列化后的用户信息
        :return: user
    """
    # 创建序列化器
    s = Serializer(settings.SECRET_KEY, constants.VERIFY_EMAIL_TOKEN_EXPIRES)
    # 使用loads对token进行解密
    try:
        data = s.loads(token)
    except BadData:
        return None
    else:

        # 从data中取出user_id和email
        user_id = data.get('user_id')
        email = data.get('email')
        # 使用user_id和email查询出要验证邮箱的用户
        try:
            user = User.objects.get(id=user_id,email=email)
            # 用户不存在抛出异步
        except User.DoesNotExist:
            return None
        # 返回用户
        else:
            return user


def generate_verify_email_url(user):
    """
    生成邮箱激活链接
    :param user: 当前登录用户
    :return:  http://www.meiduo.site:8000/emails/verification/?token=eyJhbGciOiJIUzUxMiIsImlhdCI6MTU1ODA2MDE0MSwiZXhwIjoxNTU4MTQ2NTQxfQ.eyJ1c2VyX2lkIjoxLCJlbWFpbCI6InpoYW5namllc2hhcnBAMTYzLmNvbSJ9.y1jaafj2Mce-LDJuNjkTkVbichoq5QkfquIAhmS_Vkj6m-FLOwBxmLTKkGG0Up4eGGfkhKuI11Lti0n3G9XI3Q
    """

    # 1. 创建序列化器对象
    s = Serializer(settings.SECRET_KEY, constants.VERIFY_EMAIL_TOKEN_EXPIRES)
    # 准备加密的字典数据
    data = {'user_id':user.id, 'email': user.email}
    # 2.使用dumps对字典进行加密
    token = s.dumps(data).decode()
    # 3.返回加密后的邮箱验证链接
    return settings.EMAIL_VERIFY_URL + '?token=' + token



def get_user_by_account(account):
    """
    通过账号获取用户
    :param account: 用户名或者手机号
    :return: user
    """
    try:
        if re.match(r'^1[3-9]\d{9}$', account):
            # account == 手机号
            user = User.objects.get(mobile=account)
        else:
            # account == 用户名
            user = User.objects.get(username=account)
    except User.DoesNotExist:
        return None
    else:
        return user


class UsernameMobileBackend(ModelBackend):
    """自定义用户认证后端"""

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        重写用户用户认证的方法
        :param request:
        :param username: 用户名或手机
        :param password: 密码明文
        :param kwargs: 额外参数
        :return: user
        """

        # 查询用户
        user = get_user_by_account(username)
        # 如果可以查询到用户，好需要校验密码是否正确
        if user and user.check_password(password):
            return user
        else:
            return None



