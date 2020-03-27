from thingsboard_gateway.things.meter import MeterDataDefine
from thingsboard_gateway.things.meter.gb_meter_protocol import CJT188Protocol
from thingsboard_gateway.things.meter.nan_suo import NsDataDefineName


class NsReadDataResponse(CJT188Protocol):
    """
    读表数据返回
    """

    def __init__(self):
        super().__init__()
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Default, 2))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Seq, 1))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.TotalUsed, 4))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Remaining, 4))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.TotalPurchases, 4))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Times, 1))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Status0, 1))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Status1, 1))


class NsReadUser1Response(CJT188Protocol):
    """
    读用户参数1返回 终端用户号、表号
    """

    def __init__(self):
        super().__init__()
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Default, 2))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Seq, 1))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.UnitCode, 2))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.UserNo, 2))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.MeterNo, 1))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Empty, 2))


class NsReadUser2Response(CJT188Protocol):
    """
    读用户参数2返回 读终端超容值、透支量、报警量
    """

    def __init__(self):
        super().__init__()
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Default, 2))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Seq, 1))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.AlarmValue, 1))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Overdraft, 1))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Exceed, 1))
        self.data_defines.append(MeterDataDefine(NsDataDefineName.Empty, 4))