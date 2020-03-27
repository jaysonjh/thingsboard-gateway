import time

from pymodbus.constants import Defaults
from pymodbus.datastore import ModbusServerContext
from pymodbus.device import ModbusControlBlock, ModbusAccessControl, ModbusDeviceIdentification
from pymodbus.factory import ServerDecoder, ClientDecoder
from pymodbus.framer.socket_framer import ModbusSocketFramer
from pymodbus.bit_write_message import WriteMultipleCoilsResponse, WriteSingleCoilResponse
from pymodbus.register_read_message import ReadRegistersResponseBase
from pymodbus.register_write_message import WriteMultipleRegistersResponse, WriteSingleRegisterResponse
from twisted.internet.protocol import ServerFactory

from thingsboard_gateway.connectors.modbus.bytes_modbus_downlink_converter import BytesModbusDownlinkConverter
from thingsboard_gateway.connectors.modbus.bytes_modbus_uplink_converter import BytesModbusUplinkConverter
from thingsboard_gateway.gateway.tb_schedule_service import TBScheduleService
from thingsboard_gateway.twisted.usr.usr_protocol import UsrProtocol
from thingsboard_gateway.tb_utility.tb_utility import TBUtility, log

from apscheduler.schedulers.background import BackgroundScheduler


class UsrProtocolFactory(ServerFactory):
    """
    有人设备通讯工厂
    """
    protocol = UsrProtocol

    def __init__(self, gateway, connector, store, framer=None, identity=None, **kwargs):
        self._clients = dict()
        self._gateway = gateway
        self._devices = {}
        # self._connector = connector
        self._tokens = set()
        self._usrConfig = None
        # 定时任务
        self._jobs = {}
        self._schedulerService = TBScheduleService(BackgroundScheduler())

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
        self._schedulerService.start()

    def stopFactory(self):
        self._schedulerService.stop(wait=False)

    def addClient(self, addr, protocol, token):
        self._clients[addr] = {'protocol': protocol, 'token': token}
        if token is not None:
            devices = self.getDevices(token)
            for device in devices:
                for attr in device['devices']:
                    self._addPollPeriodJob(attr)

    def delClient(self, addr, token):
        if token is None:
            raise Exception('Token must be not None')
        del self._clients[addr]
        devices = self.getDevices(token)
        for device in devices:
            for attr in device['devices']:
                self._removePollPeriodJob(attr)
                self._addPollPeriodJob(attr)

    def updateClient(self, addr, protocol, token):
        if token is None:
            raise Exception('Token must be not None')
        self._clients[addr] = {'protocol': protocol, 'token': token}
        devices = self.getDevices(token)
        for device in devices:
            for attr in device['devices']:
                self._removePollPeriodJob(attr)
                self._addPollPeriodJob(attr)

    def clear(self):
        self._clients = dict()
        self._devices = {}

    def hasToken(self, token):
        return token in self._tokens

    def hasDeviceOnline(self, name):
        device = self._devices.get(name, None)
        if device is not None:
            return self.hasToken(device['token'])
        else:
            return False

    def getDevice(self, name, addr=None, unit_id=None):
        """
        按名字或者地址+ID查询单个设备
        :param name: 设备名称
        :param addr: 地址
        :param unit_id: id
        :return: 设备信息
        """
        # 优先使用Name查询
        if name is not None:
            return self._devices.get(name, None)
        clients = self._clients
        token = clients[addr]['token']
        devices = list(
            filter(lambda x: self._devices[x]['token'] == token and self._devices[x]['config'].get('unitId') == unit_id,
                   self._devices))
        if devices is not None and len(devices) > 0:
            return devices[0]
        else:
            return None

    def getDevices(self, token):
        """
        根据token获取设备列表
        :param token: token
        :return: 设备配置信息
        """
        devices = list(
            filter(lambda x: self._devices[x]['token'] == token,
                   self._devices))
        return devices

    def addDevices(self, config, connector):
        token = config['accessToken']
        self._tokens.add(token)
        if token is not None:
            for device in config['devices']:
                if config.get("converter") is not None:
                    converter = TBUtility.check_and_import('tcp', self._config["converter"])(device)
                else:
                    converter = BytesModbusUplinkConverter(device)
                if config.get("downlink_converter") is not None:
                    downlink_converter = TBUtility.check_and_import('tcp',
                                                                    self._config["downlink_converter"])(device)
                else:
                    downlink_converter = BytesModbusDownlinkConverter(device)
                if device.get('deviceName') not in self._gateway.get_devices():
                    self._gateway.add_device(device.get('deviceName'), {"connector": connector},
                                             device_type=device.get("deviceType"))
                    self._devices[device["deviceName"]] = {"config": device,
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

                break

    def updateDevices(self, config, connector):
        token = config['accessToken']
        self._tokens.add(token)
        if token is not None:
            # 1. 先删除之前添加的设备，避免存在脏设备。
            pre_gateway_devices = filter(
                lambda x: self._gateway[x]["connector"].get_name() == connector.get_name(),
                self._gateway.get_devices())
            if pre_gateway_devices is not None:
                for pre_device in pre_gateway_devices:
                    self._gateway.del_device(pre_device.get('deviceName'))

            devices = {k: v for k, v in self._devices.items() if v['token'] == token}
            for device in list(devices.keys()):
                del self._devices[device]

            # 2. 新增设备，重置所有的信息
            for device in config['devices']:
                if config.get("converter") is not None:
                    converter = TBUtility.check_and_import('tcp', self._config["converter"])(device)
                else:
                    converter = BytesModbusUplinkConverter(device)
                if config.get("downlink_converter") is not None:
                    downlink_converter = TBUtility.check_and_import('tcp', self._config["downlink_converter"])(device)
                else:
                    downlink_converter = BytesModbusDownlinkConverter(device)

                if device.get('deviceName') not in self._gateway.get_devices():
                    self._gateway.add_device(device.get('deviceName'), {"connector": connector},
                                             device_type=device.get("deviceType"))
                if device.get('deviceName') not in self._devices:
                    self._devices[device["deviceName"]] = {"config": device,
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

                break

    def removeDevices(self, config):
        token = config['accessToken']
        self._tokens.remove(token)
        if token is not None:
            devices = {k: v for k, v in self._devices.items() if v['token'] == token}
            for device in list(devices.keys()):
                self._gateway.del_device(device)
                del self._devices[device]

    def _getProtocol(self, token):
        client = list(filter(lambda x: self._clients[x]['token'] == token, self._clients))
        if client is not None:
            return client[0]['protocol']
        return None

    def _poll_period_handler(self, name, poll_type):
        device = self.getDevice(name)
        if device is not None:
            unit_id = device['config']['unitId']

            # 上传数据
            def __pollPeriodCallback(response):
                if response is not None:
                    current_time = time.time()
                    log.debug("Checking %s for device %s", poll_type, device)
                    device["next_" + poll_type + "_check"] = current_time + device["config"][
                        poll_type + "PollPeriod"] / 1000
                    log.debug(response)
                    converted_data = device["converter"].convert(config=None, data=response)
                    to_send = {"deviceName": converted_data["deviceName"],
                               "deviceType": converted_data["deviceType"]}
                    if device["config"].get("sendDataOnlyOnChange"):

                        if to_send.get("telemetry") is None:
                            to_send["telemetry"] = []
                        if to_send.get("attributes") is None:
                            to_send["attributes"] = []
                        for telemetry_dict in converted_data["telemetry"]:
                            for key, value in telemetry_dict.items():
                                if device["last_telemetry"].get(key) is None or device["last_telemetry"][key] != value:
                                    device["last_telemetry"][key] = value
                                    to_send["telemetry"].append({key: value})

                        for attribute_dict in converted_data["attributes"]:
                            for key, value in attribute_dict.items():
                                if device["last_attributes"].get(key) is None or device["last_attributes"][
                                    key] != value:
                                    device["last_attributes"][key] = value
                                    to_send["attributes"].append({key: value})

                        if to_send.get("attributes") or to_send.get("telemetry"):
                            self._gateway.send_to_storage(self.get_name(), to_send)
                        else:
                            log.debug("Data has not been changed.")

                    elif device["config"].get("sendDataOnlyOnChange") is None or not device["config"].get(
                            "sendDataOnlyOnChange"):
                        # if converted_data["telemetry"] != self.__devices[device]["telemetry"]:
                        device["last_telemetry"] = converted_data["telemetry"]
                        to_send["telemetry"] = converted_data["telemetry"]
                        # if converted_data["attributes"] != self.__devices[device]["attributes"]:
                        device["last_telemetry"] = converted_data["attributes"]
                        to_send["attributes"] = converted_data["attributes"]
                        self._gateway.send_to_storage(self.get_name(), to_send)

            # 失败处理
            def __pollPeriodErrback(response):
                if response is not None:
                    log.debug(response)

            try:
                protocol = self._getProtocol(device['token'])
                if protocol is not None:
                    _ = protocol.poll_period_to_device(device, unit_id, poll_type,
                                                       callback=__pollPeriodCallback, errback=__pollPeriodErrback)
                else:
                    log.error("Received poll period request, but client[%s] is not connected.",
                              device['token'])
            except Exception as e:
                log.exception(e)

    def server_side_rpc_handler(self, config, content):
        device = self.getDevice(content["device"])
        if device is not None:
            token = device.get('token')

            def __rpcCallback(response):
                if response is not None:
                    log.debug(response)
                    if type(response) in (WriteMultipleRegistersResponse,
                                          WriteMultipleCoilsResponse,
                                          WriteSingleCoilResponse,
                                          WriteSingleRegisterResponse):
                        response = True
                    else:
                        response = False
                    log.debug(response)
                    self.__gateway.send_rpc_reply(content["device"],
                                                  content["data"]["id"],
                                                  {content["data"]["method"]: response})

            def __rpcErrback(response):
                if response is not None:
                    log.debug(response)

            try:
                protocol = self._getProtocol(token)
                if protocol is not None:
                    deffer = protocol.server_side_rpc_handler(device, device["unitId"],
                                                              callback=__rpcCallback, errback=__rpcErrback)
                    if deffer is None:
                        log.error("Received rpc request, but handler failed")
                else:
                    log.error("Received rpc request, but client[%s] is not connected.",
                              token)
            except Exception as e:
                log.exception(e)
        else:
            log.error("Received rpc request, but device %s not found in config for %s.",
                      config['name'],
                      content["data"].get("method"))

    def _addPollPeriodJob(self, device):
        attributesPollPeriod = device["attributesPollPeriod"]
        timeseriesPollPeriod = device["timeseriesPollPeriod"]
        deviceName = device.get('deviceName')
        if attributesPollPeriod is not None:
            attributesPollPeriod = attributesPollPeriod / 1000 if attributesPollPeriod / 1000 >= 1 else 1
            job_id = '%s:%s' % (deviceName, 'attributes')
            self._jobs[job_id] = {"time": attributesPollPeriod,
                                  "type": "attributes",
                                  "name": deviceName}
            self._schedulerService.add_job(self._poll_period_handler, 'interval',
                                           seconds=attributesPollPeriod, args=[deviceName, 'attributes'],
                                           id=job_id)

        if timeseriesPollPeriod is not None:
            timeseriesPollPeriod = timeseriesPollPeriod / 1000 if timeseriesPollPeriod / 1000 >= 1 else 1
            job_id = '%s:%s' % (deviceName, 'timeseries')
            self._jobs[job_id] = {"time": timeseriesPollPeriod,
                                  "type": "timeseries",
                                  "name": deviceName}
            self._schedulerService.add_job(self._poll_period_handler, 'interval',
                                           seconds=timeseriesPollPeriod, args=[deviceName, 'timeseries'],
                                           id=job_id)

    def _removePollPeriodJob(self, device):
        deviceName = device.get('deviceName')

        # 处理attributes Job
        jobs = {k: v for k, v in self._jobs.items() if v['name'] == deviceName and v['type'] == 'attributes'}
        if jobs is not None and len(list(jobs)) > 0:
            self._schedulerService.remove_job('%s:%s' % (deviceName, 'attributes'))

        # 处理timeseries Job
        jobs = {k: v for k, v in self._jobs.items() if v['name'] == deviceName and v['type'] == 'timeseries'}
        if jobs is not None and len(list(jobs)) > 0:
            self._schedulerService.remove_job('%s:%s' % (deviceName, 'timeseries'))
