from ..entities.event import BaseEvent
from ..entities.dispatcher import BaseDispatcher
from ..interfaces.dispatcher import DispatcherInterface
from pydantic import BaseModel # pylint: disable=no-name-in-module

class ExceptionThrowed(BaseEvent):
    exception: Exception
    event: BaseEvent

    class Dispatcher(BaseDispatcher):
        @staticmethod
        def catch(interface: DispatcherInterface):
            if interface.annotation == interface.event.exception.__class__:
                return interface.event.exception
            if interface.name == "event":
                return interface.event.event