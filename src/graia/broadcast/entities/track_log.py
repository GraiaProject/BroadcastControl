from enum import Enum
from typing import TYPE_CHECKING, Any, List, Literal, Tuple, Union

if TYPE_CHECKING:
    from graia.broadcast.typing import T_Dispatcher


class TrackLogType(Enum):
    LookupStart = 0
    LookupEnd = 1

    Continue = 2
    Result = 3

    RequirementCrashed = 4


T_TrackLogItem = Union[
    Tuple[Literal[TrackLogType.LookupStart], str, Any, Any],
    Tuple[Literal[TrackLogType.Continue], str, Any],
    Tuple[Literal[TrackLogType.Result], str, "T_Dispatcher"],
    Tuple[Literal[TrackLogType.LookupEnd], str],
    Tuple[Literal[TrackLogType.RequirementCrashed], str],
]


class TrackLog:
    __slots__ = ("log", "fluent_success")

    def __init__(self) -> None:
        self.log = []
        self.fluent_success = True

    log: List[T_TrackLogItem]
    fluent_success: bool
