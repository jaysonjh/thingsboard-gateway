from enum import Enum, unique


@unique
class CJT188MeterType(Enum):
    """
     国标GB-CJ/T188协议,水电表类型
    """

    # 冷水表
    Water = 0x10
    # 热水表
    HotWater = 0x11
    # 直饮水表
    DirectWater = 0x12
    # 中水水表
    IntermediateWater = 0x13
    # 大口径水表
    Woltex = 0x14
    # 热量表(计热量)
    HotHeat = 0x20
    # 热量表(计冷量)
    CoolHeat = 0x21
    # 燃气表
    Gas = 0x30
    # 电表
    Electricity = 0x40
    # 集抄器
    Collector = 0x80


class MeterDataDefine(object):
    """
    数据域的数据
    """

    def __init__(self, name, size, data=None):
        self.name = name
        self.size = size
        self.data = data
