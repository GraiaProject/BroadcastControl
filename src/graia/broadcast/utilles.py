import inspect
from collections import UserList
from contextlib import contextmanager
from contextvars import ContextVar, Token
from functools import lru_cache
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

from .entities.dispatcher import BaseDispatcher

if TYPE_CHECKING:
    from graia.broadcast.entities.event import Dispatchable
    from graia.broadcast.interfaces.dispatcher import DispatcherInterface
    from graia.broadcast.typing import T_Dispatcher


async def run_always_await(any_callable: Union[Awaitable, Callable]):
    if inspect.isawaitable(any_callable):
        return await any_callable
    else:
        return any_callable


async def run_always_await_safely(callable, *args, **kwargs):
    if iscoroutinefunction(callable):
        return await callable(*args, **kwargs)
    return callable(*args, **kwargs)


T = TypeVar("T")
D = TypeVar("D", type(None), Any)


class Ctx(Generic[T]):
    current_ctx: ContextVar[T]

    def __init__(self, name: str) -> None:
        self.current_ctx = ContextVar(name)

    def get(self, default: Optional[Union[T, D]] = None) -> Union[T, D]:
        return self.current_ctx.get(default)

    def set(self, value: T):
        return self.current_ctx.set(value)

    def reset(self, token: Token):
        return self.current_ctx.reset(token)

    @contextmanager
    def use(self, value: T):
        token = self.set(value)
        yield
        self.reset(token)


def printer(value: Any):
    print(value)
    return value


class DebugList(UserList):
    def extend(self, item) -> None:
        print(item)
        return super().extend(item)

    def append(self, item) -> None:
        print(item)
        return super().append(item)

    def insert(self, i: int, item) -> None:
        print(i, item)
        return super().insert(i, item)


def group_dict(iterable: Iterable, key_callable: Callable[[Any], Any]):
    temp = {}
    for i in iterable:
        k = key_callable(i)
        temp.setdefault(k, [])
        temp[k].append(i)
    return temp


cache_size = 4096


@lru_cache(cache_size)
def argument_signature(callable_target: Callable):
    return [
        (
            name,
            param.annotation if param.annotation is not inspect.Signature.empty else None,
            param.default if param.default is not inspect.Signature.empty else None,
        )
        for name, param in inspect.signature(callable_target).parameters.items()
    ]


@lru_cache(cache_size)
def is_asyncgener(o):
    return inspect.isasyncgenfunction(o)


@lru_cache(cache_size)
def iscoroutinefunction(o):
    return inspect.iscoroutinefunction(o)


@lru_cache(cache_size)
def isasyncgen(o):
    return inspect.isasyncgen(o)


@lru_cache(None)
def dispatcher_mixin_handler(dispatcher: Union[Type[BaseDispatcher], BaseDispatcher]) -> "List[T_Dispatcher]":
    unbound_mixin = getattr(dispatcher, "mixin", [])
    result: "List[T_Dispatcher]" = [dispatcher]

    for i in unbound_mixin:
        if issubclass(i, BaseDispatcher):
            result.extend(dispatcher_mixin_handler(i))
        else:
            result.append(i)
    return result


class NestableIterable(Iterable[T]):
    index_stack: list
    iterable: List[T]

    def __init__(self, iterable: List[T]) -> None:
        self.iterable = iterable
        self.index_stack = [-1]

    def __iter__(self):
        index = self.index_stack[-1]
        self.index_stack.append(index)

        start_offset = index + 1
        try:
            for self.index_stack[-1], content in enumerate(
                self.iterable[start_offset:],
                start=start_offset,
            ):
                yield content
        finally:
            self.index_stack.pop()


class _CoveredObjectMeta(type):
    if TYPE_CHECKING:
        __origin__: Any

    def __instancecheck__(self, __instance: Any) -> bool:
        return isinstance(__instance, self.__origin__.__class__)


class CoveredObject(metaclass=_CoveredObjectMeta):
    def __init__(self, obj: Any, cover_params: Dict[str, Any]):
        for k, v in cover_params.items():
            if k.startswith("__") and k.endswith("__"):
                raise TypeError("you should not cover any magic method.")
            setattr(self, k, v)
        self.__origin__ = obj
        self.__covered__ = cover_params

    def __getattribute__(self, key: str):
        if key == "__origin__" or key == "__covered__":
            return super().__getattribute__(key)
        covered = super().__getattribute__("__covered__")
        if key in covered:
            return covered[key]
        origin = super().__getattribute__("__origin__")
        return getattr(origin, key)

    def __call__(self, *args, **kwargs):
        origin = super().__getattribute__("__origin__")
        return origin(*args, **kwargs)


class CoverDispatcher(BaseDispatcher):
    origin: "T_Dispatcher"
    event: "Dispatchable"

    def __init__(self, origin: "T_Dispatcher", event: "Dispatchable") -> None:
        self.origin = origin
        self.event = event

    async def beforeExecution(self, interface: "DispatcherInterface"):
        if self.origin.beforeExecution:
            return await self.origin.beforeExecution(CoveredObject(interface, {"event": self.event}))  # type: ignore

    async def catch(self, interface: "DispatcherInterface"):
        return await self.origin.catch(CoveredObject(interface, {"event": self.event}))  # type: ignore

    async def afterDispatch(
        self, interface: "DispatcherInterface", exception: Optional[Exception], tb: Optional[TracebackType]
    ):
        if self.origin.afterDispatch:
            return await self.origin.afterDispatch(CoveredObject(interface, {"event": self.event}), exception, tb)  # type: ignore

    async def afterExecution(
        self, interface: "DispatcherInterface", exception: Optional[Exception], tb: Optional[TracebackType]
    ):
        if self.origin.afterExecution:
            return await self.origin.afterExecution(CoveredObject(interface, {"event": self.event}), exception, tb)  # type: ignore
