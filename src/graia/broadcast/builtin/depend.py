from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager, contextmanager
from inspect import isasyncgenfunction, isgeneratorfunction
from types import TracebackType
from typing import AsyncContextManager, Callable, ContextManager

from graia.broadcast.interfaces.dispatcher import (
    DispatcherInterface as DispatcherInterface,
)

from ..entities.decorator import Decorator
from ..entities.dispatcher import BaseDispatcher
from ..entities.exectarget import ExecTarget
from ..entities.signatures import Force
from ..interfaces.decorator import DecoratorInterface
from ..interfaces.dispatcher import DispatcherInterface as DispatcherInterface


class Depend(Decorator):
    pre = True

    exec_target: ExecTarget
    cache: bool = False

    raw: Callable

    def __init__(self, callable: Callable, *, cache=False):
        self.cache = cache
        self.raw = callable

        if isgeneratorfunction(callable) or isgeneratorfunction(getattr(callable, "__call__", None)):
            callable = contextmanager(callable)
        elif isasyncgenfunction(callable) or isasyncgenfunction(getattr(callable, "__call__", None)):
            callable = asynccontextmanager(callable)

        self.exec_target = ExecTarget(callable)

    async def target(self, interface: DecoratorInterface):
        cache: dict = interface.local_storage["_depend_cached_results"]
        if self.raw in cache:
            return cache[self.raw]

        result_tier1 = await interface.dispatcher_interface.broadcast.Executor(
            target=self.exec_target,
            dispatchers=interface.dispatcher_interface.dispatchers,
            depth=interface.dispatcher_interface.depth + 1,
        )
        stack: AsyncExitStack = interface.local_storage["_depend_lifespan_manager"]

        if isinstance(result_tier1, ContextManager):
            result = stack.enter_context(result_tier1)
            cache[self.raw] = result
        elif isinstance(result_tier1, AsyncContextManager):
            result = await stack.enter_async_context(result_tier1)
            cache[self.raw] = result
        else:
            result = result_tier1
            if self.cache:
                cache[self.raw] = result

        return Force(result)


class DependDispatcher(BaseDispatcher):
    async def beforeExecution(self, interface: DispatcherInterface):
        interface.local_storage["_depend_lifespan_manager"] = AsyncExitStack()
        interface.local_storage["_depend_cached_results"] = {}

    async def catch(self, interface: DispatcherInterface):
        return

    async def afterExecution(
        self,
        interface: DispatcherInterface,
        exception: Exception | None,
        tb: TracebackType | None,
    ):
        stack: AsyncExitStack = interface.local_storage["_depend_lifespan_manager"]
        await stack.__aexit__(type(exception) if exception is not None else None, exception, tb)
