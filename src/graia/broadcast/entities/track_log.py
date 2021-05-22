from enum import Enum
from typing import Any, List, Tuple


class TrackLogType:
    LookupStart = 0
    LookupEnd = 1

    Continue = 2
    Result = 3

    RequirementCrashed = 4


T_TrackLogItem = Tuple[TrackLogType, Any]


class TrackLog:
    __slots__ = ("log", "fluent_success")

    def __init__(self) -> None:
        self.log = []
        self.fluent_success = True

    log: List[T_TrackLogItem]
    fluent_success: bool
