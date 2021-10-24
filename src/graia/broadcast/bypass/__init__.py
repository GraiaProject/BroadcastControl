
from typing import List, Type, Union

from .. import Broadcast
from ..entities.decorator import Decorator
from ..entities.event import Dispatchable
from ..entities.listener import Listener
from ..entities.namespace import Namespace

from ..exceptions import (
    InvalidEventName,
    RegisteredEventListener,
)

from ..typing import T_Dispatcher


class BypassBroadcast(Broadcast):
    """
    An broadcast that supports event bypassing.
    **may be unstable**
    """

    def receiver(
        self,
        event: Union[str, Type[Dispatchable]],
        priority: int = 16,
        dispatchers: List[T_Dispatcher] = None,
        namespace: Namespace = None,
        decorators: List[Decorator] = None,
    ):
        if isinstance(event, str):
            _name = event
            event = self.findEvent(event)
            if not event:
                raise InvalidEventName(_name + " is not vaild!")  # type: ignore
        priority = int(priority)

        def receiver_wrapper(callable_target):
            may_listener = self.getListener(callable_target)
            if not may_listener:
                self.listeners.append(
                    Listener(
                        callable=callable_target,
                        namespace=namespace or self.getDefaultNamespace(),
                        inline_dispatchers=dispatchers,
                        priority=priority,
                        listening_events=list(event.__mro__),
                        decorators=decorators,
                    )
                )
            else:
                if event not in may_listener.listening_events:
                    may_listener.listening_events.append(event)
                else:
                    raise RegisteredEventListener(
                        event.__name__, "has been registered!"
                    )
            return callable_target

        return receiver_wrapper
