from enum import Enum, unique


@unique
class NsDataDefineName(Enum):
    """
    南硕远程通讯数据域名称定义
    """
    # 控制
    Default = "Default"
    # 时序
    Seq = "Seq"
    # 总用量
    TotalUsed = "TotalUsed"
    # 剩余量
    Remaining = "Remaining"
    # 总购买量
    TotalPurchases = "TotalPurchases"
    # 次数
    Times = "Times"
    # 状态S0
    Status0 = "Status0"
    # 状态S1
    Status1 = "Status1"
    # 单位代码
    UnitCode = "UnitCode"
    # 用户号
    UserNo = "UserNo"
    # 表号
    MeterNo = "MeterNo"
    # 报警值
    AlarmValue = "AlarmValue"
    # 透支值
    Overdraft = "Overdraft"
    # 超容量
    Exceed = "Exceed"
    # 地址
    Address = "Address"
    # 购买量
    Purchases = "Purchases"
    # 阀门状态
    ValveStatus = "ValveStatus"
    # Reset
    Reset = "Reset"
    # 空数据
    Empty = "Empty"


@unique
class NsResetType(Enum):
    """
    南硕远程通讯初始化表状态类型定义
    """
    # 可清厂商代码
    Vendor = 0xC3
    # 可清单位代码
    Unit = 0x5A
