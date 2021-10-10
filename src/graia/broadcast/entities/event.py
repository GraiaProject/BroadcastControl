from typing import Type

from .dispatcher import BaseDispatcher


class Dispatchable:
    Dispatcher: Type[BaseDispatcher]


BaseEvent = Dispatchable
