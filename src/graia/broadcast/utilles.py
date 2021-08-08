import inspect
from contextlib import contextmanager
from contextvars import ContextVar, Token
from functools import lru_cache
from typing import (Any, Awaitable, Callable, Generic, Iterable, Type, TypeVar,
                    Union)

from .entities.dispatcher import BaseDispatcher


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

    def get(self, default: Union[D, T] = None) -> Union[T, D]:
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


def printer(value):
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

origin_isinstance = isinstance

cached_isinstance = lru_cache(1024)(isinstance)
cached_getattr = lru_cache(cache_size)(getattr)


@lru_cache(cache_size)
def argument_signature(callable_target):
    return [
        (
            name,
            param.annotation if param.annotation != inspect._empty else None,  # type: ignore
            param.default if param.default != inspect._empty else None,  # type: ignore
        )
        for name, param in dict(inspect.signature(callable_target).parameters).items()
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
def dispatcher_mixin_handler(dispatcher: Union[Type[BaseDispatcher], BaseDispatcher]):
    unbound_mixin = getattr(dispatcher, "mixin", [])
    result = [dispatcher]

    for i in unbound_mixin:
        if issubclass(i, BaseDispatcher):
            result.extend(dispatcher_mixin_handler(i))
        else:
            result.append(i)
    return result


## NestableIterable impl migrated to:
## > https://gist.github.com/GreyElaina/f9a5f998ec1c3fc7bddb811ce046d0ca
