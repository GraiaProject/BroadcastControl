from typing import Callable, List, Type

from .dispatcher import BaseDispatcher
from .event import BaseEvent
from .namespace import Namespace
from .decorater import Decorater

class Listener:
    def __init__(self,
        callable: Callable,
        namespace: Namespace,
        listening_events: List[Type[BaseEvent]],
        inline_dispatchers: List[BaseDispatcher] = None,
        headless_decoraters: List[Decorater] = None,
        priority: int = 16,
        enable_internal_access: bool = False,
    ) -> None:
        self.callable = callable
        self.namespace = namespace
        self.listening_events = listening_events
        self.inline_dispatchers = inline_dispatchers or []
        self.headless_decoraters = headless_decoraters or []
        self.priority = priority
        self.enable_internal_access = enable_internal_access

    callable: Callable
    namespace: Namespace
    listening_events: List[Type[BaseEvent]]
    inline_dispatchers: List[BaseDispatcher] = []
    headless_decoraters: List[Decorater] = []
    priority: int = 16
    enable_internal_access: bool = False