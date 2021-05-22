from dataclasses import dataclass, field
from typing import List

from .dispatcher import BaseDispatcher


@dataclass
class Namespace:
    name: str
    injected_dispatchers: List[BaseDispatcher] = field(default_factory=list)

    priority: int = 0
    default: bool = False

    hide: bool = False
    disabled: bool = False
