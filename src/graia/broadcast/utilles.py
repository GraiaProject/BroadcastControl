import inspect
from contextlib import contextmanager
from contextvars import ContextVar, Token
from functools import lru_cache
from typing import (TYPE_CHECKING, Any, Awaitable, Callable, Generic, Iterable,
                    List, Type, TypeVar, Union)

from .entities.dispatcher import BaseDispatcher

if TYPE_CHECKING:
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
D = TypeVar("D")


class Ctx(Generic[T]):
    current_ctx: ContextVar[T]

    def __init__(self, name: str) -> None:
        self.current_ctx = ContextVar(name)

    def get(self, default: Union[T, D] = None) -> Union[T, D]:
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
        self.index_stack = [0]

    def __iter__(self):
        index = self.index_stack[-1]
        self.index_stack.append(index)

        start_offset = index + index and 1
        for self.index_stack[-1], content in enumerate(
            self.iterable[start_offset:],
            start=start_offset,
        ):
            yield content
