import inspect
import itertools
from functools import lru_cache
from typing import (
    Any,
    Callable,
    Generator,
    Generic,
    Iterable,
    List,
    Tuple,
    TypeVar,
    Union,
)

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

"""
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
"""

I = TypeVar("I")


class NestableIterable(Generic[I, T]):
    iterable: Iterable[T]
    indexes: List[I]

    generator_with_index_factory: Callable[
        [Iterable[T], I], Generator[None, None, Tuple[I, T]]
    ]
    index_increase_func: Callable[[I, Iterable[T]], I]
    is_index_origin: Callable[[I], bool]

    @staticmethod
    def default_generator_factory(iterable: Iterable[T], start: I):
        return enumerate(iterable[start:], start=start)

    def __init__(
        self,
        iterable: Iterable[T],
        generator_with_index_factory: Callable[
            [Iterable[T], I], Generator[None, None, Tuple[I, T]]
        ] = None,
        index_increase_func: Callable[[I, Iterable[T]], I] = lambda x, _: x + 1,
        initial_index_value_factory: Callable[[], I] = lambda: 0,
        is_index_origin: Callable[[I], bool] = lambda x: x == 0,
    ) -> None:
        self.iterable = iterable
        self.indexes = [initial_index_value_factory()]

        self.generator_with_index_factory = (
            generator_with_index_factory or self.default_generator_factory
        )
        self.index_increase_func = index_increase_func
        self.is_index_origin = is_index_origin

    def __iter__(self):
        current_index = self.indexes[-1]
        self.indexes.append(current_index)

        if self.is_index_origin(current_index):
            start_offset = current_index
        else:
            start_offset = self.index_increase_func(current_index, self.iterable)
        # 0 = 0
        # <except 0> = index + 1
        try:
            for self.indexes[-1], content in self.generator_with_index_factory(
                self.iterable,
                start=start_offset,
            ):
                yield content
        finally:
            self.indexes.pop()
