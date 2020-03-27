import threading
from threading import Thread

from twisted.internet import reactor, endpoints, defer
from logging import getLogger

from thingsboard_gateway.twisted.usr.usr_protocol_factory import UsrProtocolFactory
from pymodbus.framer.ascii_framer import ModbusAsciiFramer
from pymodbus.framer.binary_framer import ModbusBinaryFramer
from pymodbus.framer.rtu_framer import ModbusRtuFramer
from pymodbus.framer.socket_framer import ModbusSocketFramer
from pymodbus.framer.tls_framer import ModbusTlsFramer

log = getLogger("service")


class TBTwistedService(object):
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kw):
        if not hasattr(TBTwistedService, "_instance"):
            with TBTwistedService._instance_lock:
                if not hasattr(TBTwistedService, "_instance"):
                    TBTwistedService._instance = object.__new__(cls)
                    log.info('Start TwistedService')
                    cls.__ports = {}
                    cls.__frames = {
                        'rtu': ModbusRtuFramer,
                        'ascii': ModbusAsciiFramer,
                        'socket': ModbusSocketFramer,
                        'binary': ModbusBinaryFramer,
                        'tls': ModbusTlsFramer
                    }
                    # 异步线程启动twisted服务
                    from twisted.internet import reactor
                    Thread(target=reactor.run, args=(False,)).start()
        return TBTwistedService._instance

    def __init__(self):
        pass

    def add_listen(self, gateway, config, connector):

        protocol = config['protocol']
        factory = None
        port = config['port']
        description = 'tcp:%d' % port

        # 先获取是否有listen
        client = self.__ports.get(description, None)
        if client is not None:
            listen = client.get('listen', None)
            if listen is not None:
                factory = client['factory']
                number = client['number']
                number += 1
                factory.updateDevices(config.get('devices'), connector)
                self.__ports[description] = {'listen': listen, 'factory': factory, 'number': number}
                log.info("%s connector is start listened %s", (config['name'], description))
                log.info("%d connector is listened %s" % (number, description))
                return

        # 新增listen
        # TODO: 暂时支持Usr
        if protocol == 'usr':
            factory = UsrProtocolFactory(gateway, connector, None, framer=self.__frames[config['method']])
            factory.addDevices(config, connector)

        if factory is None:
            raise Exception("Can't add listen, protocol %s is not support", protocol)

        # 不同线程需要使用此twisted的API来操作reactor
        reactor.callFromThread(self._add_listen, description, factory)

    def _add_listen(self, description, factory):
        log.info("Start listened %s", description)
        endpoint = endpoints.serverFromString(reactor, description)
        new_listen = endpoint.listen(factory)
        self.__ports[description] = {'listen': new_listen, 'factory': factory, 'number': 1}

    def rem_listen(self, config):
        port = config['port']
        description = 'tcp:%d' % port

        # 不同线程需要使用此twisted的API来操作reactor
        reactor.callFromThread(self._rem_listen, config, description)

    def _rem_listen(self, config, description):
        client = self.__ports.get(description, None)
        if client is not None:
            listen = client.get('listen', None)
            if listen is not None:
                f = client['factory']
                number = client['number']
                number -= 1
                f.removeDevices(config)
                if number <= 0:
                    log.info("Stop listen %s" % description)
                    del self.__ports[description]
                    if listen is not None:
                        listen.result.stopListening()
                else:
                    log.info("%s connector is stop listened %s", (config['name'], description))
                    log.info("Still %d connector is listened %s" % (number, description))

    def clear_listen(self):
        for k, v in self.__ports.items():
            log.info("Stop listen %s" % k)

            def _clear_listen(listen):
                # stop listen
                if listen is not None:
                    listen.result.stopListening()

            # 不同线程需要使用此twisted的API来操作reactor
            reactor.callFromThread(_clear_listen, v['listen'])
        self.__ports.clear()
        log.info("Clear listen")
        reactor.callFromThread(reactor.stop)

    def rpc_handler(self, config, content):
        port = config['port']
        description = 'tcp:%d' % port
        client = self.__ports.get(description, None)
        if client is not None:
            factory = client.get('factory')
            if factory is not None:
                # Usr 协议
                if isinstance(factory, UsrProtocolFactory):
                    factory.server_side_rpc_handler(config, content)
            else:
                log.error("Received rpc request, but factory not found in config for %s.",
                          description,
                          config["name"])
        else:
            log.error("Received rpc request, but client not found in config for %s.",
                      description,
                      config["name"])
