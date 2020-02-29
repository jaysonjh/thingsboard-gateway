from threading import Thread
from thingsboard_gateway.connectors.connector import Connector, log
from random import choice
from string import ascii_lowercase

from thingsboard_gateway.gateway.tb_twisted_service import TBTwistedService


class TcpConnector(Connector):
    """
    TCP 连接器，使用twisted的方式进行多协议支持。
    """
    def __init__(self, gateway, config, connector_type):
        self.statistics = {'MessagesReceived': 0,
                           'MessagesSent': 0}
        self.__gateway = gateway
        self.__connector_type = connector_type
        self.__config = config.get('server')
        self.__connected = False
        self.__stopped = False
        self.__name = (self.__config.get("name", 'Tcp Server ' + ''.join(choice(ascii_lowercase) for _ in range(5))))
        self.daemon = True

    def open(self):
        self.__stopped = False
        log.info("Starting Tcp connector[%s]", self.__name)
        TBTwistedService().add_listen(self.__gateway, self.__config, self)

    def is_connected(self):
        return self.__connected

    def get_name(self):
        return self.__name

    def close(self):
        self.__stopped = True
        log.info('Tcp connector[%s] has been stopped.', self.get_name())
        TBTwistedService().rem_listen(self.__config)

    def on_attributes_update(self, content):
        pass

    def server_side_rpc_handler(self, content):
        log.debug("Tcp connector received rpc request for %s with content: %s", self.get_name(), content)
        TBTwistedService().rpc_handler(self.__config, content)


