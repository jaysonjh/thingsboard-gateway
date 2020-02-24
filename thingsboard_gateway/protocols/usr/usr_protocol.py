from binascii import b2a_hex
from pymodbus.exceptions import NoSuchSlaveException
from twisted.internet.protocol import Protocol, connectionDone
from thingsboard_gateway.connectors.connector import log
from pymodbus.pdu import ModbusExceptions as merror


class UsrProtocol(Protocol):
    """
    有人云协议
    """

    def __init__(self):
        self.isValid = False
        self.__addr = None
        self.framer = None

    def dataReceived(self, data):
        if isinstance(data, bytes):
            data_str = str(data, encoding='utf-8')
            if data_str is not None and len(data_str) > 0:
                self._handlerToken(data_str)
            else:
                self._handlerModbus(data)
        else:
            raise Exception('Data is not Bytes')

    def connectionMade(self):
        self.__addr = '%s:%d' % (self.transport.getPeer().host, self.transport.getPeer().port)
        self.factory.addClient(self.__addr, self, None)
        log.debug("Client Connected [%s]" % self.__addr)
        self.framer = self.factory.framer(decoder=self.factory.decoder,
                                          client=None)

    def connectionLost(self, reason=connectionDone):
        log.debug("Client Disconnected: %s" % reason)
        self.factory.delClient(self.__addr)

    def _handlerToken(self, data):
        if self.factory.hasToken(data):
            self.factory.updateClient(self.__addr, self, data)
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
        device = self.factory.getDevice(self.__addr, request.unit_id)
        if device is not None:
            log.debug("From modbus device %s, \n%s", device["deviceName"], device)
            log.debug("With result %s", request.dncode())
        else:
            log.error("Modbus device is not exist")

    # Send to device
    def function_to_device(self, config, unit_id):
        pass

    # Callback to response
    def _execute(self, request):
        """ Executes the request and returns the result
        :param request: The decoded request message
        """
        try:
            context = self.factory.store[request.unit_id]
            response = request.execute(context)
        except NoSuchSlaveException as ex:
            log.debug("requested slave does not exist: %s" % request.unit_id)
            if self.factory.ignore_missing_slaves:
                return  # the client will simply timeout waiting for a response
            response = request.doException(merror.GatewayNoResponse)
        except Exception as ex:
            log.debug("Datastore unable to fulfill request: %s" % ex)
            response = request.doException(merror.SlaveFailure)

        response.transaction_id = request.transaction_id
        response.unit_id = request.unit_id
        self._send(response)

    def _send(self, message):
        """ Send a request (string) to the network
        :param message: The unencoded modbus response
        """
        if message.should_respond:
            self.factory.control.Counter.BusMessage += 1
            pdu = self.framer.buildPacket(message)
            if log.isEnabledFor(log.DEBUG):
                log.debug('send: %s' % b2a_hex(pdu))
            return self.transport.write(pdu)
