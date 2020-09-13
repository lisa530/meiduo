from django.core.files.storage import Storage
from django.conf import settings


class FastDFSStorage(Storage):
    """自定义文件存储类"""

    def __init__(self, fdfs_base_url=None):
        """文件存储类的初始化方法"""
        # self.fdfs_base_url = fdfs_base_url
        self.fdfs_base_url = fdfs_base_url or settings.FDFS_BASE_URL

    def _open(self, name, mode='rb'):
        """
        打开文件时会被调用:文档告诉我必须重写
        :param name: 文件路径
        :param mode: 文件打开方式
        :return: None
        """
        pass

    def _save(self, name, content):
        """
        保存文件时会被调用的：文档告诉我必须重写
        :param name:   文件路径
        :param content:  文件二进制内容
        :return: None
        """
        pass

    def url(self, name):
        """
         返回文件的全路径
        :param name: 文件相对路径
        :return: 文件的全路径（http://192.168.3.74:8888/group1/M00/00/00/wKhnnlxw_gmAcoWmAAEXU5wmjPs35.jpeg）
        """
        # return 'http://192.168.3.74:8888/' + name
        return self.fdfs_base_url + name