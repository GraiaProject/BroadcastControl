from typing import Any, Callable, List
from pydantic import BaseModel
from graia.broadcast.abstract.interfaces.dispatcher import IDispatcherInterface


class MappingRule(BaseModel):
    mode: Callable[[IDispatcherInterface], bool]
    value: Any

    @classmethod
    def nameEquals(cls, name, value):
        return cls(mode=lambda x: x.name == name, value=value)

    @classmethod
    def annotationEquals(cls, annotation, value):
        return cls(mode=lambda x: x.annotation == annotation, value=value)

    @classmethod
    def defaultEquals(cls, default, value):
        return cls(mode=lambda x: x.default == default, value=value)
