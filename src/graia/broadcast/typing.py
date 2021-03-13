from typing import Any, Callable, TYPE_CHECKING, Type, Union

if TYPE_CHECKING:
    from graia.broadcast.interfaces.dispatcher import DispatcherInterface

T_Dispatcher = Union[
    Type["BaseDispatcher"], "BaseDispatcher", Callable[["DispatcherInterface"], Any]
]

T_Dispatcher_Callable = Callable[["DispatcherInterface"], Any]

from graia.broadcast.entities.dispatcher import BaseDispatcher
