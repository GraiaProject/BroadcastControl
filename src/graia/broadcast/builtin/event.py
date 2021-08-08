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
        def catch(interface: "DispatcherInterface"):
            if interface.annotation == interface.event.exception.__class__:  # type: ignore
                return interface.event.exception  # type: ignore
            if interface.name == "event":
                return interface.event.event  # type: ignore
