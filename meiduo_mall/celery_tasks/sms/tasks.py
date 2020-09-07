# 定义发短信短信的函数
from celery_tasks.sms.yuntongxun.ccp_sms import CCP
from celery_tasks.sms import constants
from celery_tasks.main import celery_app

# 使用装饰器装饰异步任务,给异步任务取一个别名保证celery能识别任务
@celery_app.task(name='send_sms_code')
def send_sms_code(mobile,sms_code):
    """
    发送短信验证码的异步任务
    :param mobile: 手机号
    :param sms_code: 短信验证码
    :return: 成功：0 失败: -1
    """
    # mobile:接收短信手机号， sms_code短信  短信过期时间: 300秒 // 60(5分钟内有效) , 模板id
    send_ret = CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES // 60], constants.SEND_SMS_TEMPLATE_ID)
    return send_ret
