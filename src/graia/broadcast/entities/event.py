from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from .dispatcher import BaseDispatcher


class Dispatchable:
    Dispatcher: Type["BaseDispatcher"]


BaseEvent = Dispatchable
