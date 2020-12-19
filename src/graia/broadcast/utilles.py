import inspect
import itertools
from functools import lru_cache
from typing import Any, Callable, List, Union

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

cached_isinstance = lru_cache(10240)(isinstance)
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
def isgeneratorfunction(o):
    return inspect.isgeneratorfunction(o)


@lru_cache(cache_size)
def iscoroutinefunction(o):
    return inspect.iscoroutinefunction(o)


@lru_cache(cache_size)
def isasyncgen(o):
    return inspect.isasyncgen(o)


@lru_cache(cache_size)
def isgenerator(o):
    return inspect.isgenerator(o)


async def whatever_gen_once(any_gen, *args, **kwargs):
    if inspect.isasyncgenfunction(any_gen):
        # 如果是异步生成器函数
        async for i in any_gen(*args, **kwargs):
            return i
    elif inspect.isgeneratorfunction(any_gen) and not inspect.iscoroutinefunction(
        any_gen
    ):
        # 同步生成器
        for i in any_gen(*args, **kwargs):
            return i
    elif inspect.isgenerator(any_gen):
        for i in any_gen:
            return i
    elif inspect.isasyncgen(any_gen):
        async for i in any_gen:
            return i


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
