from typing import List

from pydantic import BaseModel  # pylint: disable=no-name-in-module

from .dispatcher import BaseDispatcher


class Namespace(BaseModel):
    name: str
    injected_dispatchers: List[BaseDispatcher] = []

    priority: int = 0
    default: bool = False
    
    hide: bool = False
    disabled: bool = False

    class Config:
        arbitrary_types_allowed = True
