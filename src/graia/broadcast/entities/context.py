import copy
from typing import Any, Callable, Dict, Generator, List, TypeVar, Union

from graia.broadcast.utilles import NestableIterable

from ..typing import DEFAULT_LIFECYCLE_NAMES, T_Dispatcher

T = TypeVar("T")
I = TypeVar("I")

LF_TEMPLATE = {i: list() for i in DEFAULT_LIFECYCLE_NAMES}


class ExecutionContext:
    __slots__ = ("event", "lifecycle_refs", "dispatchers", "path")

    lifecycle_refs: Dict[str, List[Callable]]
    dispatchers: List[T_Dispatcher]

    path: NestableIterable

    def __init__(self, dispatchers: List[T_Dispatcher]):
        self.dispatchers = dispatchers

        self.lifecycle_refs = LF_TEMPLATE.copy()
