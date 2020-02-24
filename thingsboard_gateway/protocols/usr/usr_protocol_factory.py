from pymodbus.constants import Defaults
from pymodbus.datastore import ModbusServerContext
from pymodbus.device import ModbusControlBlock, ModbusAccessControl, ModbusDeviceIdentification
from pymodbus.factory import ServerDecoder
from pymodbus.framer.socket_framer import ModbusSocketFramer
from twisted.internet.protocol import ServerFactory

from thingsboard_gateway.connectors.modbus.bytes_modbus_downlink_converter import BytesModbusDownlinkConverter
from thingsboard_gateway.connectors.modbus.bytes_modbus_uplink_converter import BytesModbusUplinkConverter
from thingsboard_gateway.protocols.usr.usr_protocol import UsrProtocol
from thingsboard_gateway.tb_utility.tb_utility import TBUtility, log


class UsrProtocolFactory(ServerFactory):
    """
    有人设备通讯工厂
    """
    protocol = UsrProtocol

    def __init__(self, gateway, connector, store, framer=None, identity=None, **kwargs):
        self.__clients = dict()
        self.__gateway = gateway
        self.__devices = {}
        self.__connector = connector
        self.__tokens = set()
        self.__usrConfig = None
        self.__addAllDevices()

        # Modbus
        self.decoder = ServerDecoder()
        self.framer = framer(self.decoder) or ModbusSocketFramer(self.decoder)
        self.store = store or ModbusServerContext()
        self.control = ModbusControlBlock()
        self.access = ModbusAccessControl()
        self.ignore_missing_slaves = kwargs.get('ignore_missing_slaves', Defaults.IgnoreMissingSlaves)

        if isinstance(identity, ModbusDeviceIdentification):
            self.control.Identity.update(identity)

        log.debug('Start Usr Factory:', self)

    def startFactory(self):
        # TODO: 清除所有的连接
        pass

    def stopFactory(self):
        self.clear()

    def addClient(self, addr, protocol, token):
        self.__clients[addr] = (protocol, token)

    def delClient(self, addr):
        del self.__clients[addr]

    def updateClient(self, addr, protocol, token):
        if token is None:
            raise Exception('Token must be not None')
        self.__clients[addr] = (protocol, token)
        self.__tokens.add(token)

    def clear(self):
        self.__clients = dict()
        self.__devices = {}

    def hasToken(self, token):
        return token in self.__tokens

    def hasDeviceOnline(self, name):
        device = self.__devices[name]
        if device is not None:
            return self.hasToken(device['token'])
        else:
            return False

    def getDevice(self, addr, unit_id):
        devices = self.__clients
        _, token = devices[addr]
        devices = list(filter(lambda x: devices[x]['token'] == token and devices[x]['config'].get('unitId') == unit_id,
                              devices))
        if devices is not None and len(devices) > 0:
            return devices[0]
        else:
            return None

    def addDevices(self, config):
        token = config['accessToken']
        if token is not None:
            for device in config['devices']:
                if config.get("converter") is not None:
                    converter = TBUtility.check_and_import(self._connector_type, self.__config["converter"])(device)
                else:
                    converter = BytesModbusUplinkConverter(device)
                if config.get("downlink_converter") is not None:
                    downlink_converter = TBUtility.check_and_import(self._connector_type,
                                                                    self.__config["downlink_converter"])(device)
                else:
                    downlink_converter = BytesModbusDownlinkConverter(device)
                if device.get('deviceName') not in self.__gateway.get_devices():
                    self.__gateway.add_device(device.get('deviceName'), {"connector": self.__connector},
                                              device_type=device.get("deviceType"))
                    self.__devices[device["deviceName"]] = {"config": device,
                                                            "token": token,
                                                            "converter": converter,
                                                            "downlink_converter": downlink_converter,
                                                            "next_attributes_check": 0,
                                                            "next_timeseries_check": 0,
                                                            "telemetry": {},
                                                            "attributes": {},
                                                            "last_telemetry": {},
                                                            "last_attributes": {}
                                                            }
                # TODO: 新增定时任务
                break

    def updateDevices(self, config):
        token = config['accessToken']
        if token is not None:
            # 1. 先删除之前添加的设备，避免存在脏设备。
            pre_gateway_devices = filter(
                lambda x: self.__gateway[x]["connector"].get_name() == self.__connector.get_name(),
                self.__gateway.get_devices())
            if pre_gateway_devices is not None:
                for pre_device in pre_gateway_devices:
                    self.__gateway.del_device(pre_device.get('deviceName'))

            devices = filter(lambda x: self.__devices[x]['token'] == token, self.__devices)
            for device in devices:
                del self.__devices[device.get('deviceName')]
                # TODO: 删除定时任务

            # 2. 新增设备，重置所有的信息
            for device in config['devices']:
                if config.get("converter") is not None:
                    converter = TBUtility.check_and_import(self._connector_type, self.__config["converter"])(device)
                else:
                    converter = BytesModbusUplinkConverter(device)
                if config.get("downlink_converter") is not None:
                    downlink_converter = TBUtility.check_and_import(self._connector_type,
                                                                    self.__config["downlink_converter"])(device)
                else:
                    downlink_converter = BytesModbusDownlinkConverter(device)

                if device.get('deviceName') not in self.__gateway.get_devices():
                    self.__gateway.add_device(device.get('deviceName'), {"connector": self.__connector},
                                              device_type=device.get("deviceType"))
                if device.get('deviceName') not in self.__devices:
                    self.__devices[device["deviceName"]] = {"config": device,
                                                            "token": token,
                                                            "converter": converter,
                                                            "downlink_converter": downlink_converter,
                                                            "next_attributes_check": 0,
                                                            "next_timeseries_check": 0,
                                                            "telemetry": {},
                                                            "attributes": {},
                                                            "last_telemetry": {},
                                                            "last_attributes": {}
                                                            }
                # TODO: 重置定时任务
                break

    def removeDevices(self, config):
        token = config['accessToken']
        if token is not None:
            devices = filter(lambda x: self.__devices[x]['token'] == token, self.__devices)
            for device in devices:
                self.__gateway.del_device(device.get('deviceName'))
                del self.__devices[device.get('deviceName')]
                # TODO: 删除定时任务
