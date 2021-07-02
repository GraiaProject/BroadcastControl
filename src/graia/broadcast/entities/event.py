import inspect
from typing import TYPE_CHECKING, Any, Protocol, Tuple, TypeVar, Union

if TYPE_CHECKING:
    from .dispatcher import BaseDispatcher


class Dispatchable:
    Dispatcher: "BaseDispatcher"


BaseEvent = Dispatchable
