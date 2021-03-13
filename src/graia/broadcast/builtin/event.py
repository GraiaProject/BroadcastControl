from typing import TYPE_CHECKING
from ..entities.dispatcher import BaseDispatcher
from ..entities.event import BaseEvent

if TYPE_CHECKING:
    from graia.broadcast.interfaces.dispatcher import DispatcherInterface


class ExceptionThrowed(BaseEvent):
    exception: Exception
    event: BaseEvent

    class Dispatcher(BaseDispatcher):
        @staticmethod
        def catch(interface: "DispatcherInterface"):
            if interface.annotation == interface.event.exception.__class__:
                return interface.event.exception
            if interface.name == "event":
                return interface.event.event
