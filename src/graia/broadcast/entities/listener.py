from typing import Callable, List, Optional, Type

from ..typing import T_Dispatcher
from .decorator import Decorator
from .event import Dispatchable
from .exectarget import ExecTarget
from .namespace import Namespace


class Listener(ExecTarget):
    namespace: Namespace
    listening_events: List[Type[Dispatchable]]
    priority: int

    def __init__(
        self,
        callable: Callable,
        namespace: Namespace,
        listening_events: List[Type[Dispatchable]],
        inline_dispatchers: Optional[List[T_Dispatcher]] = None,
        decorators: Optional[List[Decorator]] = None,
        priority: int = 16,
    ) -> None:
        super().__init__(callable, inline_dispatchers, decorators)

        self.namespace = namespace
        self.listening_events = listening_events
        self.priority = priority
