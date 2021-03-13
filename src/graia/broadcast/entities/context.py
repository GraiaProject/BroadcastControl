import itertools

from typing import Any, Callable, Dict, List
from graia.broadcast.utilles import NestableIterable

from ..typing import T_Dispatcher


def path_generator_factory(iterable: List[List["T_Dispatcher"]], start: int):
    return enumerate(list(itertools.chain(*iterable))[start:])


class ExecutionContext:
    event: "BaseEvent"
    _index: int
    lifecycle_refs: Dict[str, List[Callable]]
    dispatchers: List[T_Dispatcher]

    def __init__(self, dispatchers: List[T_Dispatcher], event: "BaseEvent") -> None:
        self.event = event
        self._index = 0
        self.dispatchers = dispatchers

        self.lifecycle_refs = {}


class ParameterContext:
    name: str
    annotation: Any
    default: Any

    dispatchers: List[T_Dispatcher]

    def __init__(self, name, annotation, default, dispatchers, using_path) -> None:
        self.name = name
        self.annotation = annotation
        self.default = default
        self.dispatchers = dispatchers
        self.path = NestableIterable(using_path, path_generator_factory)

    def __repr__(self) -> str:
        return (
            "<ParameterContext name={0} annotation={1} default={2} locald={3}".format(
                self.name, self.annotation, self.default, self.dispatchers
            )
        )


from .event import BaseEvent
