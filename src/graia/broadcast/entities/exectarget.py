from typing import Callable, Dict, List, Tuple, Union

from ..typing import T_Dispatcher
from .decorater import Decorater


class ExecTarget:
    def __init__(
        self,
        callable: Callable,
        inline_dispatchers: List[T_Dispatcher] = None,
        headless_decoraters: List[Decorater] = None,
        enable_internal_access: bool = False,
    ) -> None:
        self.callable = callable
        self.inline_dispatchers = inline_dispatchers or []
        self.headless_decoraters = headless_decoraters or []
        self.enable_internal_access = enable_internal_access

        self.dispatcher_statistics = {"total": 0, "statistics": {}}

    callable: Callable
    inline_dispatchers: List[T_Dispatcher] = []
    headless_decoraters: List[Decorater] = []
    enable_internal_access: bool = False

    dispatcher_statistics: Dict[str, Union[int, Dict]]
