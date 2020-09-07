from django.shortcuts import render
from django.views import View
from django_redis import get_redis_connection
from django import http

from . import constants
from verifications.libs.captcha.captcha import  captcha
from meiduo_mall.utils.response_code import RETCODE
import random,logging
from verifications.libs.yuntongxun.ccp_sms import CCP
from celery_tasks.sms.tasks import send_sms_code


# 创建日志输出器
logger = logging.getLogger('django')


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


class SMSCodeView(View):
    """短信验证码"""

    def get(self,request,mobile):
        """
        发送短信业务逻辑
        :param request:
        :param mobile:
        :return:
        """
        # 1.接收参数
        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('uuid')

        # 2 校验参数
        # mobile不需要在视图中校验，在url中使用正则校验成功才能进入视图
        if not all([image_code_client, uuid]):
            return http.HttpResponseForbidden('缺少必传参数')

        # 创建redis连接对象
        redis_conn = get_redis_connection('verify_code')
        # 3. 从redis中获取 发送短信验证码标记
        send_flag = redis_conn.get('send_flag_%s' % mobile)
        # 判断用户是否频繁发送短信验证码
        if send_flag:
            return http.JsonResponse({'code':RETCODE.THROTTLINGERR, 'errmsg': '发送短信过于频繁'})

        # 4.提取图形验证码
        # 从redis中提取图形验证码，以前怎么存现在怎么取
        image_code_server = redis_conn.get('img_%s' % uuid)
        # 如果图形验证码失效, 提示错误信息
        if image_code_server is None:
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图形验证码已失效'})
        # 存在,则删除图形验证码
        redis_conn.delete('img_%s' % uuid)

        # 5.对比图形验证码，用户输入的和redis中保存的图形验证码进行比较
        image_code_server = image_code_server.decode() # 将bytes转成字符串
        if image_code_client.lower() != image_code_server.lower(): # 转小写
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '输入图形验证码有误'})

        # 6. 生成短信验证码
        # 生成随机6位数短信验证码
        sms_code = '%06d' % random.randint(0,999999)
        logger.info(sms_code)  # 手动的输出日志，记录短信验证码
        # 保存短信验证码
        # sms_13155950101 key  短信验证码过期时间 短信验证码的值
        # redis_conn.setex('sms_%s' % mobile, constants.SMS_CODE_REDIS_EXPIRES,sms_code)

        # 保存发送短信验证码的标记
        # redis_conn.setex('send_flag_%s' % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)

        # 创建redis管道
        # 将命令添加到队列中
        pl = redis_conn.pipeline()
        # 保存短信验证码
        pl.setex('sms_%s' % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        # 执行短信验证码标记
        pl.setex('send_flag_%s' % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)
        # 执行
        pl.execute()

        # 发送短信,调用 CCP
        # mobile:接收短信手机号， sms_code短信  短信过期时间: 300秒 // 60(5分钟内有效) , 模板id
        # CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES // 60], constants.SEND_SMS_TEMPLATE_ID)

        # 使用celery异步发送短信验证码
        send_sms_code.delay(mobile,sms_code) # 千万不要忘记写delay

        # 6. 响应结果
        return http.JsonResponse({'code': RETCODE.OK,'errmsg': '发送短信成功'})


