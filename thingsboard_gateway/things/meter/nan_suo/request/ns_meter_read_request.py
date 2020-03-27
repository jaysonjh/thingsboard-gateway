from thingsboard_gateway.things.meter import MeterDataDefine
from thingsboard_gateway.things.meter.nan_suo import NsDataDefineName
from thingsboard_gateway.things.meter.gb_meter_protocol import CJT188Protocol


class NasReadDataRequest(CJT188Protocol):
    """
    读表数据
    """

    def __init__(self, address, device_type, seq):
        super().__init__()
        self.address = bytes.fromhex(address)
        self.device_type = device_type
        self.control_code = 0x01

        self.data_defines.append(MeterDataDefine(NsDataDefineName.Default, 2, data=bytes([0x1F, 0x90])))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Seq, 1, data=bytes([seq])))


class NsoReadAddressRequest(CJT188Protocol):
    """
    读表地址
    """
    def __init__(self, device_type, seq):
        super().__init__()
        self.address = bytes([0xAA] * 7)
        self.device_type = device_type
        self.control_code = 0x03

        self.data_defines.append(MeterDataDefine(NsDataDefineName.Default, 2, data=bytes([0x0A, 0x81])))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Seq, 1, data=bytes([seq])))


class NsReadUser1Request(CJT188Protocol):
    """
    读用户参数1- 读终端用户号、表号
    """
    def __init__(self,address, device_type, seq):
        super().__init__()
        self.address = bytes.fromhex(address)
        self.device_type = device_type
        self.control_code = 0x03

        self.data_defines.append(MeterDataDefine(NsDataDefineName.Default, 2, data=bytes([0xAA, 0x81])))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Seq, 1, data=bytes([seq])))


class NsReadUser2Request(CJT188Protocol):
    """
    读用户参数2- 读终端超容值、透支量、报警量
    """
    def __init__(self,address, device_type, seq):
        super().__init__()
        self.address = bytes.fromhex(address)
        self.device_type = device_type
        self.control_code = 0x03

        self.data_defines.append(MeterDataDefine(NsDataDefineName.Default, 2, data=bytes([0xB0, 0x81])))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Seq, 1, data=bytes([seq])))