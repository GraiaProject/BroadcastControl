from typing import Any, Callable, Type, Union

T_Dispatcher = Union[
    Type["BaseDispatcher"], "BaseDispatcher", Callable[["IDispatcherInterface"], Any]
]

T_Dispatcher_Callable = Callable[["IDispatcherInterface"], Any]

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.abstract.interfaces.dispatcher import IDispatcherInterface
