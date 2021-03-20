from enum import IntEnum, auto
from typing import Any, List, Tuple, NamedTuple


class TrackLogType(IntEnum):
    LookupStart = auto()
    LookupEnd = auto()

    Continue = auto()
    Result = auto()

    RequirementCrashed = auto()


T_TrackLogItem = Tuple[TrackLogType, Any]


class TrackLog:
    __slots__ = ("log", "fluent_success")

    def __init__(self) -> None:
        self.log = []
        self.fluent_success = True

    log: List[T_TrackLogItem]
    fluent_success: bool
