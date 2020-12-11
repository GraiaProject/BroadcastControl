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


@lru_cache(None)
def argument_signature(callable_target):
    return [
        (
            name,
            param.annotation if param.annotation != inspect._empty else None,
            param.default if param.default != inspect._empty else None,
        )
        for name, param in dict(inspect.signature(callable_target).parameters).items()
    ]


cache_size = None


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

import sys

class debug_context():
    """ Debug context to trace any function calls inside the context """

    def __init__(self, name):
        self.name = name

    def __enter__(self):
        print('Entering Debug Decorated func')
        # Set the trace function to the trace_calls function
        # So all events are now traced
        sys.settrace(self.trace_calls)

    def __exit__(self, *args, **kwargs):
        # Stop tracing all events
        sys.settrace = None

    def trace_calls(self, frame, event, arg): 
        # We want to only trace our call to the decorated function
        if event != 'call':
            return
        elif frame.f_code.co_name != self.name:
            return
        # return the trace function to use when you go into that 
        # function call
        return self.trace_lines

    def trace_lines(self, frame, event, arg):
        # If you want to print local variables each line
        # keep the check for the event 'line'
        # If you want to print local variables only on return
        # check only for the 'return' event
        if event not in ['line', 'return']:
            return
        co = frame.f_code
        func_name = co.co_name
        line_no = frame.f_lineno
        filename = co.co_filename
        #line_text = open(filename, "r", encoding="utf-8").readlines()[line_no-1][:-1]
        local_vars = frame.f_locals
        print ('callable [{0}] [{1}] on {2}'.format(func_name, 
                                                  event,
                                                  line_no))

def debug_decorator(func):
    """ Debug decorator to call the function within the debug context """
    def decorated_func(*args, **kwargs):
        with debug_context(func.__name__):
            return_value = func(*args, **kwargs)
        return return_value
    return decorated_func