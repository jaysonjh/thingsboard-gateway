from threading import Thread

from twisted.internet import reactor, endpoints
from logging import getLogger

from thingsboard_gateway.protocols.usr.usr_protocol_factory import UsrProtocolFactory
from pymodbus.framer.ascii_framer import ModbusAsciiFramer
from pymodbus.framer.binary_framer import ModbusBinaryFramer
from pymodbus.framer.rtu_framer import ModbusRtuFramer
from pymodbus.framer.socket_framer import ModbusSocketFramer
from pymodbus.framer.tls_framer import ModbusTlsFramer

log = getLogger("service")


class TBTwistedService(object):
    _instance = None

    def __new__(cls, *args, **kw):
        if cls._instance is None:
            cls._instance = object.__new__(cls, *args, **kw)
            # 异步线程启动twisted服务
            from twisted.internet import reactor
            Thread(target=reactor.run, args=(False,)).start()
            log.debug('Start TwistedService')
            cls.__ports = {}
            cls.__frames = {
                'rtu': ModbusRtuFramer,
                'ascii': ModbusAsciiFramer,
                'socket': ModbusSocketFramer,
                'binary': ModbusBinaryFramer,
                'tls': ModbusTlsFramer
            }
        return cls._instance

    def __init__(self):
        pass

    def add_listen(self, gateway, config, connector):

        protocol = config['protocol']
        factory = None
        port = config['port']
        description = 'tcp:%d' % port

        # 先获取是否有listen
        client = self.__ports[description]
        listen = client['listen']
        if listen is not None:
            factory = client['factory']
            number = client['number']
            number += 1
            factory.updateDevices(config.get('devices'))
            self.__ports[description] = {'listen': listen, 'factory': factory, 'number': number}
            log.debug("%s connector is start listened %s", (config['name'], description))
            log.debug("%d connector is listened %s" % (number, description))
            return

        # 新增listen
        # TODO: 暂时支持Usr
        if protocol == 'usr':
            factory = UsrProtocolFactory(gateway, connector, self.__frames[config['method']])
            factory.addDevices(config.get('devices'))

        if factory is None:
            raise Exception("Can't add listen, protocol %s is not support", protocol)

        def _add_listen(des, fact):
            log.debug("%s connector is start listened %s", (config['name'], description))
            endpoint = endpoints.serverFromString(reactor, des)
            new_listen = endpoint.listen(fact)
            self.__ports[description] = {'listen': new_listen, 'factory': fact, 'number': 1}

        # 不同线程需要使用此twisted的API来操作reactor
        reactor.callFromThread(_add_listen, description, factory)

    def rem_listen(self, config):
        port = config['port']
        description = 'tcp:%d' % port

        def _rem_listen(des):
            client = self.__ports[des]
            listen = client['listen']
            if listen is not None:
                f = client['factory']
                number = client['number']
                number -= 1
                f.removeDevices(config)
                if number <= 0:
                    log.debug("Stop listen %s" % description)
                    del self.__ports[description]
                    if listen is not None:
                        listen.result.stopListening()
                else:
                    log.debug("%s connector is stop listened %s", (config['name'], description))
                    log.debug("Still %d connector is listened %s" % (number, description))

        # 不同线程需要使用此twisted的API来操作reactor
        reactor.callFromThread(_rem_listen, description)

    def clear_listen(self):
        log.debug("Clear listen")
        for _, v in self.__ports.items():
            def _clear_listen(listen):
                # stop listen
                if listen is not None:
                    listen.result.stopListening()

            # 不同线程需要使用此twisted的API来操作reactor
            reactor.callFromThread(_clear_listen, v)
        self.__ports.clear()

    def rpc_handler(self, config, content):
        port = config['port']
        description = 'tcp:%d' % port
        _, factory, _ = self.__ports[description]
        if factory is not None:
            # Usr 协议
            if isinstance(factory, UsrProtocolFactory):
                factory.server_side_rpc_handler(config, content)
        else:
            log.error("Received rpc request, but factory not found in config for %s.",
                      description,
                      config["name"])
