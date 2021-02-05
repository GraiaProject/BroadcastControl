from typing import Callable, List, Type

from .dispatcher import BaseDispatcher
from .event import BaseEvent
from .namespace import Namespace
from .decorator import Decorator

from .exectarget import ExecTarget


class Listener(ExecTarget):
    def __init__(
        self,
        callable: Callable,
        namespace: Namespace,
        listening_events: List[Type[BaseEvent]],
        inline_dispatchers: List[BaseDispatcher] = None,
        headless_decorators: List[Decorator] = None,
        priority: int = 16,
        enable_internal_access: bool = False,
    ) -> None:
        super().__init__(
            callable, inline_dispatchers, headless_decorators, enable_internal_access
        )
        self.namespace = namespace
        self.listening_events = listening_events
        self.priority = priority

    namespace: Namespace
    listening_events: List[Type[BaseEvent]]
    priority: int = 16
