import asyncio
from ..entities.namespace import Namespace
from ..utilles import Ctx
from ..interfaces.decorator import DecoratorInterface
from ..interfaces.dispatcher import DispatcherInterface
from typing import Iterable
from ..entities.listener import Listener
from .. import Broadcast


class BypassBroadcast(Broadcast):
    """
    An broadcast that supports event bypassing.
    **may be unstable**
    """
    def __init__(
        self,
        *,
        loop: asyncio.AbstractEventLoop = None,
        debug_flag: bool = False,
    ):
        self.loop = loop or asyncio.get_event_loop()
        self.default_namespace = Namespace(name="default", default=True)
        self.debug_flag = debug_flag
        self.namespaces = []
        self.listeners = []
        self.event_ctx = Ctx("bcc_event_ctx")
        self.dispatcher_interface = DispatcherInterface(self)
        self.decorator_interface = DecoratorInterface(self.dispatcher_interface)
        self.dispatcher_interface.execution_contexts[0].dispatchers.insert(
            0, self.decorator_interface
        )

        @self.dispatcher_interface.inject_global_raw
        async def _(interface: DispatcherInterface):
            if isinstance(interface.event, interface.annotation):
                return interface.event
            elif interface.annotation is Broadcast:
                return interface.broadcast
            elif interface.annotation is DispatcherInterface:
                return interface

    def default_listener_generator(self, event_class) -> Iterable[Listener]:
        return list(
            filter(
                lambda x: all(
                    [
                        not x.namespace.hide,
                        not x.namespace.disabled,
                        issubclass(event_class, tuple(x.listening_events)),
                    ]
                ),
                self.listeners,
            )
        )
