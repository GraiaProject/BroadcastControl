import inspect
from typing import Any, Callable, List

from iterwrapper import IterWrapper
from pydantic import BaseModel  # pylint: disable=no-name-in-module


async def async_enumerate(iterable, start: int = 0):
    count = start
    async for i in iterable:
        yield (count, i)
        count += 1

async def run_always_await(any_callable):
    if inspect.iscoroutine(any_callable):
        return await any_callable
    else:
        return any_callable

def printer(value):
    print(value)
    return value

def iw_group(iw: IterWrapper, key: Callable[[Any], Any]):
    temp = {}
    for i in iw:
        k = key(i)
        temp.setdefault(k, [])
        temp[k].append(i)
    return IterWrapper(temp.values()).map(list)

def argument_signature(callable_target):
    return [
        (name,
        param.annotation if param.annotation != inspect._empty else None,
        param.default if param.default != inspect._empty else None)
        for name, param in dict(inspect.signature(callable_target).parameters).items()
    ]
