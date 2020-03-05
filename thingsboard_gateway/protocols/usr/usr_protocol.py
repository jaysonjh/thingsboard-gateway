import time
from binascii import b2a_hex
from threading import Timer

from thingsboard_gateway.connectors.connector import log

from twisted.internet import defer
from twisted.internet.protocol import Protocol, connectionDone
from twisted.python.failure import Failure

from pymodbus.bit_read_message import ReadCoilsRequest, ReadDiscreteInputsRequest
from pymodbus.register_read_message import ReadHoldingRegistersRequest, ReadInputRegistersRequest, \
    ReadRegistersResponseBase
from pymodbus.register_write_message import WriteMultipleRegistersRequest, WriteSingleRegisterRequest
from pymodbus.bit_write_message import WriteMultipleCoilsRequest, WriteSingleCoilRequest
from pymodbus.compat import byte2int
from pymodbus.exceptions import NoSuchSlaveException, ConnectionException
from pymodbus.framer.socket_framer import ModbusSocketFramer
from pymodbus.transaction import DictTransactionManager, FifoTransactionManager

from thingsboard_gateway.tb_utility.tb_utility import threadsafe_function


class UsrProtocol(Protocol):
    """
    有人云协议
    """

    def __init__(self):
        self._is_valid = False
        self._addr = None
        self._token = None
        self._connected = False
        self._timeout = 10
        self._functions = {
            1: ReadCoilsRequest,
            2: ReadDiscreteInputsRequest,
            3: ReadHoldingRegistersRequest,
            4: ReadInputRegistersRequest,
            5: WriteSingleCoilRequest,
            6: WriteSingleRegisterRequest,
            15: WriteMultipleCoilsRequest,
            16: WriteMultipleRegistersRequest
        }
        self._timeoutDeffer = defer.Deferred()
        self._requests = []
        self.framer = None
        self.transaction = None

    def dataReceived(self, data):
        log.debug("Received data: " + " ".join([hex(byte2int(x)) for x in data]))
        self._timeoutDeffer.callback('dataReceived')
        if self._is_valid:
            # 验证成功
            unit = self.framer.decode_data(data).get("uid", 0)
            self.framer.processIncomingPacket(data, self._handleResponse,
                                              unit=unit)
        else:
            # 首次获取数据，验证注册码
            data_str = str(data, encoding='ascii')
            if data_str is not None and len(data_str) > 0:
                self._handlerToken(data_str)

    def connectionMade(self):
        # 初始化Framer
        self.framer = self.factory.framer
        # 初始化TransactionT
        if isinstance(self.framer, ModbusSocketFramer):
            self.transaction = DictTransactionManager(self)
        else:
            self.transaction = FifoTransactionManager(self)

        self._addr = '%s:%d' % (self.transport.getPeer().host, self.transport.getPeer().port)
        self.factory.addClient(self._addr, self, None)
        log.debug("Client Connected [%s]" % self._addr)
        self._connected = True

    def connectionLost(self, reason=connectionDone):
        log.debug("Client Disconnected: %s" % reason)
        self.factory.delClient(self._addr, self._token)

    def _handlerToken(self, data):
        if self.factory.hasToken(data):
            self._is_valid = True
            self._token = data
            self.factory.updateClient(self._addr, self, data)
        else:
            log.error("This connections token[%s] is not valid." % data)
            self.transport.loseConnection()

    def _handlerModbus(self, data):
        if not self.factory.control.ListenOnly:
            units = self.factory.store.slaves()
            single = self.factory.store.single
            self.framer.processIncomingPacket(data, self._dataHandler,
                                              single=single,
                                              unit=units)

    def _dataHandler(self, request):
        device = self.factory.getDevice(self._addr, request.unit_id)
        if device is not None:
            log.debug("From modbus device %s, \n%s", device["deviceName"], device)
            log.debug("With result %s", request.dncode())
        else:
            log.error("Modbus device is not exist")

    # Send to device
    def _function_to_device(self, config, unit_id, callback=None, errback=None):
        function_code = config.get('functionCode')
        request = None
        if function_code in (1, 2, 3, 4):
            registerCount = config.get("registerCount", 1)
            request = self._functions[function_code](unit_id, registerCount)
        elif function_code in (5, 6, 15, 16):
            payload = config["payload"]
            request = self._functions[function_code](unit_id, payload)

        if request is not None:
            log.debug("To modbus device %s, \n%s", config["deviceName"], config)
            return self._execute(request, callback, errback)
        else:
            log.error("Unknown Modbus function with code: %i", function_code)
            return None

    def poll_period_to_device(self, config, unit_id, poll_type, callback=None, errback=None):
        current_time = time.time()
        device = config['config']
        try:
            if device.get(type) is not None:
                if config["next_" + poll_type + "_check"] < current_time:
                    #  Reading data from device
                    for interested_data in range(len(device[poll_type])):
                        current_data = device[poll_type][interested_data]
                        current_data["deviceName"] = device.get('deviceName')

                        def __internalCallback(response):
                            device_responses = {"timeseries": {},
                                                "attributes": {},
                                                }
                            if not isinstance(response, ReadRegistersResponseBase) and response.isError():
                                log.exception(response)
                            device_responses[poll_type][device["tag"]] = {"data_sent": current_data,
                                                                          "input_data": response}
                            if callback is not None:
                                callback(device_responses)

                        _ = self._function_to_device(current_data, unit_id, callback=__internalCallback,
                                                     errback=errback)
        except Exception as e:
            log.exception(e)

    def server_side_rpc_handler(self, config, content, callback=None, errback=None):
        rpc_command_config = config["config"]["rpc"].get(content["data"].get("method"))
        if rpc_command_config.get('bit') is not None:
            rpc_command_config["functionCode"] = 6
            rpc_command_config["unitId"] = config["config"]["unitId"]

        if rpc_command_config is not None:
            rpc_command_config["payload"] = self._devices[content["device"]]["downlink_converter"].convert(
                rpc_command_config, content)
            return self._function_to_device(rpc_command_config, rpc_command_config['unit_id'], callback=callback,
                                            errback=errback)
        else:
            log.error("Received rpc request, but method %s not found in config for %s.",
                      content["data"].get("method"),
                      config["config"]['deviceName'])
            return None

    @threadsafe_function
    def _execute(self, request, config, callback, errback):
        """
        Starts the producer to send the next request to
        consumer.write(Frame(request))
        """
        request.transaction_id = self.transaction.getNextTID()
        d = self._buildResponse(request.transaction_id)
        if callback is not None:
            d.addCallback(callback)
        if errback is not None:
            d.addErrback(errback)

        if len(self._requests) > 0:
            # 加入队列
            self._requests.append({'request': request, 'config': config})
        else:
            # 立即请求
            self._send()
        return d

    def _buildResponse(self, tid):
        """
        Helper method to return a deferred response
        for the current request.

        :param tid: The transaction identifier for this response
        :returns: A defer linked to the latest request
        """
        if not self._connected:
            return defer.fail(Failure(
                ConnectionException('Client is not connected')))

        d = defer.Deferred()
        self.transaction.addTransaction(d, tid)
        return d

    def _handleResponse(self, reply, **kwargs):
        """
        Handle the processed response and link to correct deferred
        :param reply: The reply to process
        """
        if reply is not None:
            tid = reply.transaction_id
            handler = self.transaction.getTransaction(tid)
            if handler:
                handler.callback(reply)
            else:
                log.debug("Unrequested message: " + str(reply))

    def _timeoutHandler(self, res=None):
        if res is None:
            log.debug("Wait Response time out!")
        else:
            log.debug("Error: %s", res)

        if len(self._requests) > 0:
            request = self._requests.pop(0)
            handler = self.transaction.getTransaction(request['request'].transaction_id)
            handler.errback(request['config'])
        self._nextHandler('Next')

    def _cancelHandler(self, res):
        log.debug("timeoutDeffer Cancel")

    def _nextHandler(self, res):
        if len(self._requests) > 0:
            log.debug("Next Request")
            self._send()
        else:
            log.debug("Request Queue is empty! Waiting new request")

    def _send(self):
        request = self._requests[0]
        packet = self.framer.buildPacket(request['request'])
        log.debug("send: " + " ".join([hex(byte2int(x)) for x in packet]))
        self.transport.write(packet)
        self._createRequestDeffer()

    def _createRequestDeffer(self):
        self._timeoutDeffer = None
        self._timeoutDeffer = defer.Deferred(canceller=self._cancelHandler)
        self._timeoutDeffer.addErrback(self._timeoutHandler)
        self._timeoutDeffer.addCallback(self._nextHandler)
        self._timeoutDeffer.addTimeout(timeout=self._timeout)

    def close(self):
        """
        Closes underlying transport layer ,essentially closing the client
        :return:
        """
        if self.transport and hasattr(self.transport, "close"):
            self.transport.close()
        self._timeoutDeffer.cancel()
        self._connected = False
