import weakref

from typing import Any, Callable, Dict, List, Set, Type, Union
from graia.broadcast.entities.source import DispatcherSource
from graia.broadcast.utilles import cached_isinstance

from ..typing import T_Dispatcher


class ExecutionContext:
    source: DispatcherSource[T_Dispatcher, "ExecutionContext"]
    always_dispatchers: Set[Union["BaseDispatcher", Type["BaseDispatcher"]]]
    event: "BaseEvent"
    _index: int
    lifecycle_refs: Dict[str, List[Callable]]

    def __init__(self, dispatchers: List[T_Dispatcher], event: "BaseEvent") -> None:
        self.source = DispatcherSource(dispatchers, weakref.ref(self))
        self.event = event
        self._index = 0

        self.lifecycle_refs = {}
        self.always_dispatchers = set()
        self.always_dispatchers.update(
            filter(
                lambda x: cached_isinstance(x, BaseDispatcher) and x.always, dispatchers
            )
        )

    @property
    def dispatchers(self):
        return self.source.dispatchers


class ParameterContext:
    def __init__(self, name, annotation, default, dispatchers) -> None:
        self.name, self.annotation, self.default, self.source = (
            name,
            annotation,
            default,
            DispatcherSource(dispatchers, weakref.ref(self)),
        )

    def __repr__(self) -> str:
        return (
            "<ParameterContext name={0} annotation={1} default={2} locald={3}".format(
                self.name, self.annotation, self.default, self.dispatchers
            )
        )

    source: DispatcherSource[T_Dispatcher, "ParameterContext"]

    name: str
    annotation: Any
    default: Any

    @property
    def dispatchers(self) -> List[T_Dispatcher]:
        return self.source.dispatchers


from graia.broadcast.entities.dispatcher import BaseDispatcher
from .event import BaseEvent
