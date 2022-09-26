import contextlib
from typing import TYPE_CHECKING, Optional

from ..entities.dispatcher import BaseDispatcher
from ..entities.event import Dispatchable

if TYPE_CHECKING:
    from graia.broadcast.interfaces.dispatcher import DispatcherInterface


class ExceptionThrown(Dispatchable):
    exception: Exception
    event: Optional[Dispatchable]

    def __init__(self, exception: Exception, event: Optional[Dispatchable]) -> None:
        self.exception = exception
        self.event = event

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: "DispatcherInterface[ExceptionThrown]"):
            event: ExceptionThrown = interface.event
            if event.event is not None:
                with contextlib.suppress(TypeError):
                    if interface.name == "event" or isinstance(interface.event.event, interface.annotation):
                        return interface.event.event
                    if interface.name == "exception" or isinstance(interface.event.exception, interface.annotation):
                        return interface.event.exception


class EventExceptionThrown(ExceptionThrown):
    event: Dispatchable

    def __init__(self, exception: Exception, event: Dispatchable) -> None:
        self.exception = exception
        self.event = event


ExceptionThrowed = EventExceptionThrown  # backward compatibility
