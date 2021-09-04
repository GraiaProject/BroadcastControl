from typing import TYPE_CHECKING, Any, Callable, Type, Union

if TYPE_CHECKING:
    from graia.broadcast.entities.dispatcher import BaseDispatcher
    from graia.broadcast.interfaces.dispatcher import DispatcherInterface


T_Dispatcher = Union[
    Type["BaseDispatcher"], "BaseDispatcher", Callable[["DispatcherInterface"], Any]
]

T_Dispatcher_Callable = Callable[["DispatcherInterface"], Any]

DEFAULT_LIFECYCLE_NAMES = (
    "beforeExecution",
    "afterDispatch",
    "afterExecution",
)
