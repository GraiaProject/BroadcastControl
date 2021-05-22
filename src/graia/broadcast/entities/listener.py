from typing import Callable, List, Type

from .decorator import Decorator
from .dispatcher import BaseDispatcher
from .event import Dispatchable
from .exectarget import ExecTarget
from .namespace import Namespace


class Listener(ExecTarget):
    def __init__(
        self,
        callable: Callable,
        namespace: Namespace,
        listening_events: List[Type[Dispatchable]],
        inline_dispatchers: List[BaseDispatcher] = None,
        headless_decorators: List[Decorator] = None,
        priority: int = 16,
    ) -> None:
        super().__init__(callable, inline_dispatchers, headless_decorators)

        self.namespace = namespace
        self.listening_events = listening_events
        self.priority = priority

    namespace: Namespace
    listening_events: List[Type[Dispatchable]]
    priority: int
