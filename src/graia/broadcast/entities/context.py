from typing import Any, Callable, Dict, List, TypeVar

from graia.broadcast.utilles import NestableIterable

from ..typing import T_Dispatcher

T = TypeVar("T")
I = TypeVar("I")


class ExecutionContext:
    __slots__ = ("event", "dispatchers", "path", "local_storage")

    dispatchers: List[T_Dispatcher]
    path: NestableIterable
    local_storage: Dict[str, Any]

    def __init__(self, dispatchers: List[T_Dispatcher]):
        self.dispatchers = dispatchers
        self.local_storage = {}
