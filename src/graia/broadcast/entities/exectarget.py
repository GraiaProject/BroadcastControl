from typing import Callable, Dict, Hashable, List

from ..typing import T_Dispatcher
from .decorator import Decorator


class ExecTarget:
    callable: Callable
    dispatchers: List[T_Dispatcher]
    decorators: List[Decorator]

    oplog: Dict[Hashable, Dict[str, List[T_Dispatcher]]]

    def __init__(
        self,
        callable: Callable,
        inline_dispatchers: List[T_Dispatcher] = None,
        decorators: List[Decorator] = None,
    ):
        self.callable = callable
        self.dispatchers = inline_dispatchers or []
        self.decorators = decorators or []

        self.oplog = {}
