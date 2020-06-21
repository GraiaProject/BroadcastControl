from pydantic import BaseModel # pylint: disable=no-name-in-module
from typing import Callable, List
from .dispatcher import BaseDispatcher
from .namespace import Namespace
from .event import BaseEvent

class Listener(BaseModel):
    callable: Callable
    namespace: Namespace
    inline_dispatchers: List[BaseDispatcher]
    priority: int = 0
    listening_events: List[BaseEvent]

    class Config:
        arbitrary_types_allowed = True