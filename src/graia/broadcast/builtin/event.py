from typing import TYPE_CHECKING

from ..entities.dispatcher import BaseDispatcher
from ..entities.event import Dispatchable

if TYPE_CHECKING:
    from graia.broadcast.interfaces.dispatcher import DispatcherInterface


class ExceptionThrowed(Dispatchable):
    exception: Exception
    event: Dispatchable

    def __init__(self, exception: Exception, event: Dispatchable) -> None:
        self.exception = exception
        self.event = event

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: "DispatcherInterface['ExceptionThrowed']"):
            if isinstance(interface.event.exception, interface.annotation):
                return interface.event.exception
            elif isinstance(interface.event.event, interface.annotation):
                return interface.event.event
