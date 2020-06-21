from .dispatcher import DispatcherInterface
from ..entities.decorater import Decorater
from typing import Dict, Any

class DecoraterInterface:
    """Graia Broadcast Control 内部机制 Decorate 的具体管理实现
    """
    dispatcher_interface: DispatcherInterface
    local_storage: Dict[str, Any] = {}

    def __init__(self, dispatcher_interface: DispatcherInterface):
        self.dispatcher_interface = dispatcher_interface

    @property
    def name(self):
        return self.dispatcher_interface.name

    @property
    def annotation(self):
        return self.dispatcher_interface.annotation

    @property
    def default(self):
        return self.dispatcher_interface.default

    @property
    def event(self):
        return self.dispatcher_interface.event

    