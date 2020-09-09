from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from meiduo_mall.utils.response_code import RETCODE


class LoginRequiredJSONMixin(LoginRequiredMixin):
    """自定义判断用户是否登录的扩展类: 返回JSON数据"""
    def handle_no_permission(self):
        """重写handle_no_permission方法"""
        return JsonResponse({'code': RETCODE.SESSIONERR,'errmsg': '用户未登录'})
