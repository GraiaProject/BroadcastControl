from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from graia.broadcast.typing import T_Dispatcher


@dataclass
class Namespace:
    name: str
    injected_dispatchers: List["T_Dispatcher"] = field(default_factory=list)

    priority: int = 0
    default: bool = False

    hide: bool = False
    disabled: bool = False
