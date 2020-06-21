from typing import Callable, List, Type

from pydantic import BaseModel  # pylint: disable=no-name-in-module

from .dispatcher import BaseDispatcher
from .event import BaseEvent
from .namespace import Namespace


class Listener(BaseModel):
    callable: Callable
    namespace: Namespace
    inline_dispatchers: List[BaseDispatcher] = []
    priority: int = 0
    listening_events: List[Type[BaseEvent]]

    class Config:
        arbitrary_types_allowed = True
