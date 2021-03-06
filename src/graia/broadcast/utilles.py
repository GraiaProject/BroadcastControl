import inspect
import itertools
from functools import lru_cache
from typing import Any, Callable, Iterable, List, TypeVar, Union

from iterwrapper import IterWrapper

from .entities.dispatcher import BaseDispatcher


async def run_always_await(any_callable):
    if inspect.iscoroutine(any_callable):
        return await any_callable
    else:
        return any_callable


async def run_always_await_safely(callable, *args, **kwargs):
    if iscoroutinefunction(callable):
        return await callable(*args, **kwargs)
    return callable(*args, **kwargs)


def printer(value):
    print(value)
    return value


def group_dict(iw: IterWrapper, key: Callable[[Any], Any]):
    temp = {}
    for i in iw:
        k = key(i)
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
            param.annotation if param.annotation != inspect._empty else None,
            param.default if param.default != inspect._empty else None,
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


def flat_yield_from(l):
    for i in l:
        if type(i) == list:
            yield from i


@lru_cache(None)
def dispatcher_mixin_handler(dispatcher: BaseDispatcher) -> List[BaseDispatcher]:
    unbound_mixin = getattr(dispatcher, "mixin", [])
    result = [dispatcher]

    for i in unbound_mixin:
        if issubclass(i, BaseDispatcher):
            result.extend(dispatcher_mixin_handler(i))
        else:
            result.append(i)
    return result


class as_sliceable:
    def __init__(self, iterable) -> None:
        self.iterable = iterable

    def __getitem__(self, item: Union[slice, int]) -> Any:
        if isinstance(item, slice):
            return itertools.islice(self.iterable, item.start, item.stop, item.step)
        else:
            return list(itertools.islice(self.iterable, item, item + 1, None))[0]

    def __iter__(self):
        return self.iterable


T = TypeVar("T")


class NestableIterable(Iterable[T]):
    index_stack: list
    iterable: Iterable[T]

    def __init__(self, iterable: Iterable[T]) -> None:
        self.iterable = iterable
        self.index_stack = [0]

    def __iter__(self):
        index = self.index_stack[-1]
        self.index_stack.append(self.index_stack[-1])

        start_offset = index + int(bool(index))
        try:
            for self.index_stack[-1], content in enumerate(
                itertools.islice(self.iterable, start_offset, None, None),
                start=start_offset,
            ):
                yield content
        finally:
            self.index_stack.pop()

    def with_new(self, target):
        self.iterable = target
        return self
