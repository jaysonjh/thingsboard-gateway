from thingsboard_gateway.tb_utility.tb_data_utility import ns_encrypt
from thingsboard_gateway.things.meter import MeterDataDefine
from thingsboard_gateway.things.meter.gb_meter_protocol import CJT188Protocol
from thingsboard_gateway.things.meter.nan_suo import NsDataDefineName


class NsWritePurchaseResponse(CJT188Protocol):
    """
    写购买金额返回值
    购买次数 > 表内次数+1：次数错误，返回表内次数+末次购买量

    购买次数 = 表内次数+1：正常购买，返回购买后表内次数+末次购买量

    购买次数 < 表内次数+1：次数错误，返回表内次数+末次购买量
    """

    def __init__(self):
        super().__init__()
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Default, 2))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Seq, 1))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Times, 1))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Purchases, 4))

    def decode(self, sourceBytes):
        super().decode(sourceBytes)
        times = self.getDataDefine(NsDataDefineName.Times).data
        purchase = self.getDataDefine(NsDataDefineName.Purchases).data
        # 解密
        decrypt = ns_encrypt(self.address, times, purchase)
        self.getDataDefine(NsDataDefineName.Times).data = decrypt[0]
        self.getDataDefine(NsDataDefineName.Purchases).data = decrypt[1]
        return self


class NsWriteValveResponse(CJT188Protocol):

    """
    写阀门状态返回值
    """
    def __init__(self):
        super().__init__()
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Default, 2))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Seq, 1))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Status0, 1))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Status1, 1))


class NsWriteUser1Response(CJT188Protocol):
    """
    写用户参数1返回 终端用户号、表号
    """
    def __init__(self):
        super().__init__()
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Default, 2))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Seq, 1))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.UnitCode, 2))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.UserNo, 2))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.MeterNo, 1))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Empty, 2))


class NsWriteUser2Response(CJT188Protocol):
    """
    写用户参数2返回 读终端超容值、透支量、报警量
    """

    def __init__(self):
        super().__init__()
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Default, 2))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Seq, 1))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.AlarmValue, 1))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Overdraft, 1))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Exceed, 1))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Empty, 4))