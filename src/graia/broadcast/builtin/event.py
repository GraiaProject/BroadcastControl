from typing import TYPE_CHECKING

from ..entities.dispatcher import BaseDispatcher
from ..entities.event import Dispatchable

if TYPE_CHECKING:
    from graia.broadcast.interfaces.dispatcher import DispatcherInterface


class ExceptionThrowed(Dispatchable):
    exception: Exception
    event: Dispatchable

    class Dispatcher(BaseDispatcher):
        @staticmethod
        def catch(interface: "DispatcherInterface"):
            if interface.annotation == interface.event.exception.__class__:
                return interface.event.exception
            if interface.name == "event":
                return interface.event.event
