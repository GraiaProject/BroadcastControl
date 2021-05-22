from typing import TYPE_CHECKING, Any, Dict

from graia.broadcast.entities.dispatcher import BaseDispatcher

from ..entities.decorator import Decorator
from ..entities.signatures import Force
from ..utilles import cached_isinstance, run_always_await_safely

if TYPE_CHECKING:
    from graia.broadcast.interfaces.dispatcher import DispatcherInterface


class DecoratorInterface(BaseDispatcher):
    """Graia Broadcast Control 内部机制 Decorate 的具体管理实现"""

    dispatcher_interface: "DispatcherInterface"
    local_storage: Dict[Any, Any] = {}
    return_value: Any = None
    default = None

    def __init__(self, dispatcher_interface: "DispatcherInterface"):
        self.dispatcher_interface = dispatcher_interface

    @property
    def name(self):
        return self.dispatcher_interface.name

    @property
    def annotation(self):
        return self.dispatcher_interface.annotation

    @property
    def event(self):
        return self.dispatcher_interface.event

    async def catch(self, interface: "DispatcherInterface"):
        if cached_isinstance(interface.default, Decorator):
            decorator: Decorator = interface.default
            if not decorator.pre:
                # 作为 装饰
                self.return_value = await interface.lookup_param(
                    interface.name, interface.annotation, None
                )
            try:
                return Force(await run_always_await_safely(decorator.target, self))
            finally:
                if not decorator.pre:
                    self.return_value = None
