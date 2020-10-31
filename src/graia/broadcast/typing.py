from typing import Any, Callable, Type, Union
from graia.broadcast.entities.dispatcher import BaseDispatcher

T_Dispatcher = Union[
    Type[BaseDispatcher],
    BaseDispatcher,
    Callable[["DispatcherInterface"], Any]
]

T_Dispatcher_Callable = Callable[["DispatcherInterface"], Any]