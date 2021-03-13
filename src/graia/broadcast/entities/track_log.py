from enum import IntEnum, auto


class TrackLogType(IntEnum):
    LookupStart = auto()
    LookupEnd = auto()

    Continue = auto()
    Result = auto()

    RequirementCrashed = auto()
