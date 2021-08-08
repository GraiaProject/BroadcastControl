from typing import TYPE_CHECKING, Callable, List, Type

from .decorator import Decorator
from .event import Dispatchable
from .exectarget import ExecTarget
from .namespace import Namespace

if TYPE_CHECKING:
    from graia.broadcast.typing import T_Dispatcher


class Listener(ExecTarget):
    namespace: Namespace
    listening_events: List[Type[Dispatchable]]
    priority: int

    def __init__(
        self,
        callable: Callable,
        namespace: Namespace,
        listening_events: List[Type[Dispatchable]],
        inline_dispatchers: List["T_Dispatcher"] = None,
        decorators: List[Decorator] = None,
        priority: int = 16,
    ) -> None:
        super().__init__(callable, inline_dispatchers, decorators)

        self.namespace = namespace
        self.listening_events = listening_events
        self.priority = priority
