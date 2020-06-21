from pydantic import BaseModel # pylint: disable=no-name-in-module
from typing import Callable, List
from .dispatcher import BaseDispatcher
from .namespace import Namespace

class Listener(BaseModel):
    callable: Callable
    namespace: Namespace
    inline_dispatachers: List[BaseDispatcher]
    priority: int = 0