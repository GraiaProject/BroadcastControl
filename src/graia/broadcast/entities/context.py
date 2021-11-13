from typing import Any, Callable, Dict, Generator, List, TypeVar, Union

from graia.broadcast.utilles import NestableIterable

from ..typing import DEFAULT_LIFECYCLE_NAMES, T_Dispatcher

T = TypeVar("T")
I = TypeVar("I")

LF_TEMPLATE = {i: list() for i in DEFAULT_LIFECYCLE_NAMES}


class ExecutionContext:
    __slots__ = ("event", "lifecycle_refs", "dispatchers", "path")

    lifecycle_refs: Dict[str, List[Callable]]
    dispatchers: List[T_Dispatcher]

    path: NestableIterable

    def __init__(self, dispatchers: List[T_Dispatcher], path: NestableIterable):
        self.dispatchers = dispatchers
        self.path = path

        self.lifecycle_refs = LF_TEMPLATE.copy()


class ParameterContext:
    __slots__ = ("name", "annotation", "default")

    name: str
    annotation: Any
    default: Any

    def __init__(self, name, annotation, default):
        self.name = name
        self.annotation = annotation
        self.default = default

    def __repr__(self) -> str:
        return "<ParameterContext name={0} annotation={1} default={2}".format(
            self.name, self.annotation, self.default
        )
