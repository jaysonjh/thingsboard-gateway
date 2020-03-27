import logging
from abc import ABC, abstractmethod


class MeterProtocol(ABC):
    """
    水电表的协议定义
    """

    @abstractmethod
    def encode(self):
        """
        :return: 返回字节流数组
        """
        pass

    @abstractmethod
    def decode(self, sourceBytes):
        """
        :param sourceBytes: 原始数据
        :return: MeterProtocol
        """
        pass

    @abstractmethod
    def getDataDefines(self):
        """
        :return: array of MeterDataDefine
        """
        pass
