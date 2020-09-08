from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadData
from django.conf import settings
from oauth import constants_oauth


def check_access_token(access_token_openid):
    """
    反序列化
    :param access_token_openid: openid密文
    :return: openid明文
    """
    # 创建序列化器对象：序列化和反序列化的对象的参数必须是一模一样的
    s = Serializer(settings.SECRET_KEY, constants_oauth.ACCESS_TOKEN_EXPIRES)

    # 反序列化openid
    try:
        data = s.loads(access_token_openid)
    except BadData: # openid密文过期
        return None
    else:
        # 返回解密后的openid
        return data.get('openid')


def generate_access_token(openid):
    """
    对openid进行签名
    :param openid: openid明文
    :return: token(openid密文)
    """
    # 1. 创建序列化对象
    # s = Serialzier('秘钥:越复杂越安全', '过期时间')
    s = Serializer(settings.SECRET_KEY,constants_oauth.ACCESS_TOKEN_EXPIRES)
    # 准备需要加密的字典数据
    data = {'openid': openid}
    # 2. 调用dumps方法进行加密：类型是bytes
    token = s.dumps(data)
    # 3. 返回序列化后的数据
    return token.decode()