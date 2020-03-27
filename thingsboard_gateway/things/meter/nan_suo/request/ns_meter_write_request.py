from thingsboard_gateway.tb_utility.tb_data_utility import uchar_checksum, ns_encrypt
from thingsboard_gateway.things.meter import MeterDataDefine
from thingsboard_gateway.things.meter.gb_meter_protocol import CJT188Protocol
from thingsboard_gateway.things.meter.nan_suo import NsDataDefineName, NsResetType


class NsWriteAddressRequest(CJT188Protocol):
    """
    写地址
    """

    def __init__(self, device_type, seq, value, dest=None):
        super().__init__()
        if dest is not None:
            # 指定表
            self.address = bytes.fromhex(dest)
        else:
            # 广播
            self.address = bytes([0xFE] * 7)

        if not isinstance(value, str):
            raise Exception('水电表地址类型不正确，要求为字符串类型。')

        if len(value) != 7:
            raise Exception('水电表地址 %s 的长度不正确，长度不等于 7 个字节。' % value)

        self.device_type = device_type
        self.control_code = 0x15
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Default, 2, data=bytes([0x18, 0xA0])))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Seq, 1, data=bytes([seq])))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Address, 7, data=bytes.fromhex(value)))


class NsWritePurchaseRequest(CJT188Protocol):
    """
    写购买金额
    """

    def __init__(self, device_type, seq, times, purchases, address=None):
        super().__init__()
        if address is not None:
            # 指定表
            self.address = bytes.fromhex(address)
        else:
            # 广播
            self.address = bytes([0xFE] * 7)
        self.device_type = device_type
        self.control_code = 0x04
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Default, 2, data=bytes([0x13, 0xA0])))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Seq, 1, data=bytes([seq])))

        # 实际发送指令次数
        times -= 1
        if times > 255:
            times -= 255
            # 从0开始
            times -= 1

        buy = purchases.to_bytes(length=4, byteorder='little', signed=False)
        encrypt = ns_encrypt(self.address, times, buy)

        self.data_defines.append(MeterDataDefine(NsDataDefineName.Times, 1, data=bytes([encrypt[0]])))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Purchases, 4,
                                                 data=encrypt[1]))


class NsWriteValveRequest(CJT188Protocol):
    """
    写阀门状态
    """

    def __init__(self, device_type, seq, status, address=None):
        super().__init__()
        if address is not None:
            # 指定表
            self.address = bytes.fromhex(address)
        else:
            # 广播
            self.address = bytes([0xFE] * 7)
        self.device_type = device_type
        self.control_code = 0x04
        valve = 0x55 if status else 0x99
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Default, 2, data=bytes([0x17, 0xA0])))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Seq, 1, data=bytes([seq])))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.ValveStatus, 1, data=bytes([valve])))


class NsWriteResetRequest(CJT188Protocol):
    """
    初始化表状态
    0xC3 可清厂商代码，
    0x5A 可清单位代码，其它同普通清零卡
    """

    def __init__(self, device_type, seq, reset, address=None):
        super().__init__()
        if address is not None:
            # 指定表
            self.address = bytes.fromhex(address)
        else:
            # 广播
            self.address = bytes([0xFE] * 7)

        if not isinstance(reset, NsResetType):
            raise Exception('Reset参数类型不正确，要求为NsResetType。')

        self.device_type = device_type
        self.control_code = 0x04
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Default, 2, data=bytes([0x21, 0xA0])))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Seq, 1, data=bytes([seq])))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Reset, 1, data=bytes([reset.value])))


class NsWriteUser1Request(CJT188Protocol):
    """
    写用户数据1- 写终端用户号、表号
    """

    def __init__(self, device_type, seq, unit_code, user_no, meter_no, address=None):
        super().__init__()
        if address is not None:
            # 指定表
            self.address = bytes.fromhex(address)
        else:
            # 广播
            self.address = bytes([0xFE] * 7)
        self.device_type = device_type
        self.control_code = 0x04
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Default, 2, data=bytes([0x27, 0xA0])))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Seq, 1, data=bytes([seq])))

        unit_data = unit_code.to_bytes(length=2, byteorder='little', signed=False)
        self.data_defines.append(MeterDataDefine(NsDataDefineName.UnitCode, data=unit_data))

        user_data = user_no.to_bytes(length=2, byteorder='little', signed=False)
        self.data_defines.append(MeterDataDefine(NsDataDefineName.UserNo, 2, data=user_data))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.MeterNo, 1, data=bytes([meter_no])))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Empty, 2, data=bytes([0x00, 0x00])))


class NsWriteUser2Request(CJT188Protocol):
    """
    写用户数据2- 写终端超容值、透支量、报警量
    """

    def __init__(self, device_type, seq, exceed, overdraft, alarm, address=None):
        super().__init__()
        if address is not None:
            # 指定表
            self.address = bytes.fromhex(address)
        else:
            # 广播
            self.address = bytes([0xFE] * 7)
        self.device_type = device_type
        self.control_code = 0x04
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Default, 2, data=bytes([0x34, 0xA0])))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Seq, 1, data=bytes([seq])))

        self.data_defines.append(MeterDataDefine(NsDataDefineName.AlarmValue, 1, data=bytes([exceed])))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Overdraft, 1, data=bytes([overdraft])))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Exceed, 1, data=bytes([alarm])))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Empty, 4, data=bytes([0x00] * 4)))
