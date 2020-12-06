import weakref

from typing import Any, List, Set, Type, Union
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.source import DispatcherSource
from .event import BaseEvent

from ..typing import T_Dispatcher


class ExecutionContext:
    source: DispatcherSource[T_Dispatcher, "ExecutionContext"]
    always_dispatchers: Set[Union[BaseDispatcher, Type[BaseDispatcher]]]
    event: BaseEvent
    inline_generator: bool
    _index: int

    def __init__(
        self,
        dispatchers: List[T_Dispatcher],
        event: BaseEvent,
        inline_generator: bool = False,
    ) -> None:
        self.source = DispatcherSource(dispatchers, weakref.ref(self))
        self.event = event
        self.inline_generator = inline_generator
        self._index = 0

        self.always_dispatchers = set()
        for i in dispatchers:
            if isinstance(i, BaseDispatcher) and i.always:
                self.always_dispatchers.add(i)

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
