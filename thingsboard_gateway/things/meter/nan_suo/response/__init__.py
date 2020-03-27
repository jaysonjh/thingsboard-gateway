from thingsboard_gateway.things.meter.gb_meter_protocol import CJT188Protocol


class NsBaseResponse(CJT188Protocol):
    """
    读返回
    """
    def __init__(self):
        super().__init__()