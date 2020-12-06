from enum import IntEnum


class Priority(IntEnum):
    Special = -1
    Default = 16
    BuiltinListener = 8
    Logger = -2
