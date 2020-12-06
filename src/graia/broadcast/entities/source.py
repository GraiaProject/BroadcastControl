from typing import Any, Callable, Generic, Iterable, Iterator, List, TypeVar, Union
from graia.broadcast.abstract.interfaces.dispatcher import IDispatcherInterface
from graia.broadcast.typing import T_Dispatcher

T = TypeVar("T", bound=T_Dispatcher)
S = TypeVar("S")


class DispatcherSource(Generic[T, S], Iterable[T]):
    dispatchers: List[Union[T, Callable[[IDispatcherInterface], T]]]
    source: S

    def __init__(
        self,
        dispatchers: List[Union[T, Callable[[IDispatcherInterface], T]]],
        source: S = None,
    ) -> None:
        self.dispatchers = dispatchers
        self.source = source

    def __iter__(self) -> Iterator[T]:
        yield from self.dispatchers
