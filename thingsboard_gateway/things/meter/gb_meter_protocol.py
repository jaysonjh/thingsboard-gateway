import sys
from thingsboard_gateway.tb_utility.tb_data_utility import uchar_checksum
from thingsboard_gateway.things.meter.meter_protocols import MeterProtocol
from abc import ABC, abstractmethod


class CJT188Protocol(MeterProtocol, ABC):
    """
    国标GB-CJ/T188协议
    """
    # 协议头标识
    frame_head = 0x68
    # 协议尾标识
    frame_end = 0x16
    # 协议前导符
    frame_pre_head = 0xFE

    def __init__(self):
        # 设备类型
        self.device_type = 0x00
        # 数据域的数据
        self.data_defines = []
        # 地址
        self.address = None
        # 控制码
        self.control_code = 0x00
        # 数据长度
        self.size = 0
        # 数据
        self.data_area = None
        # 校验码
        self.check_sum = 0x00

    def getDataDefines(self):
        return self.data_defines

    def getDataDefine(self, name):
        """
        查询某一个数据域
        :param name: 数据域名称
        :return: MeterDataDefine / None
        """
        search = [x for x in self.data_defines if x.name == name]
        if search is not None and len(search) > 0:
            return search[0]
        else:
            return None

    def encode(self):
        if self.address is None or len(self.address) != 7:
            raise Exception('水电表地址 %s 的长度不正确，长度不等于 7 个字节。' % str(self.address))
        self._buildDataArea()
        dataArray = bytearray()

        dataArray.append(CJT188Protocol.frame_head)
        dataArray.append(self.device_type)
        dataArray.extend(self.address)
        dataArray.append(self.control_code)
        dataArray.append(self.size.to_bytes(2, 'little')[0])
        dataArray.extend(self.data_area)
        check_sum = uchar_checksum(bytes(dataArray))
        dataArray.append(check_sum)
        dataArray.append(CJT188Protocol.frame_end)
        return bytes(dataArray)

    def decode(self, sourceBytes):
        self.device_type = sourceBytes[0]
        self.address = sourceBytes[1:8]
        self.control_code = sourceBytes[8]
        self.size = sourceBytes[9]
        currentIndex = 9
        for data_define in self.data_defines:
            data_define.data = sourceBytes[currentIndex:currentIndex + data_define.size]
            currentIndex += data_define.size
        self.check_sum = sourceBytes[currentIndex]
        return self

    def _buildDataArea(self):
        if len(self.data_defines) > 0:
            dataArray = bytearray()
            for data_define in self.data_defines:
                dataArray.append(data_define.data)

            self.data_area = bytes(dataArray)
            self.size = len(self.data_area)
        else:
            self.data_area = None
            self.size = 0
