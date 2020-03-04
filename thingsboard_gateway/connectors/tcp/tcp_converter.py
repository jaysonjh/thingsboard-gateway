from thingsboard_gateway.connectors.converter import Converter, ABC, abstractmethod, log


class TcpConverter(ABC):
    @abstractmethod
    def convert(self, config, data):
        pass
