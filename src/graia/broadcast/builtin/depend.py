
from __future__ import annotations

from contextlib import (
    AsyncExitStack,
    asynccontextmanager,
    contextmanager,
)
from inspect import isasyncgenfunction, isgeneratorfunction
from types import TracebackType
from typing import Callable, ContextManager, AsyncContextManager

from graia.broadcast.interfaces.dispatcher import DispatcherInterface as DispatcherInterface

from ..entities.dispatcher import BaseDispatcher
from ..entities.exectarget import ExecTarget
from ..entities.signatures import Force


class Depend:
    target: ExecTarget
    cache: bool = False

    raw: Callable

    def __init__(self, callable: Callable, *, cache=False):
        self.cache = cache
        self.raw = callable

        if isgeneratorfunction(callable) or isgeneratorfunction(getattr(callable, "__call__", None)):
            callable = contextmanager(callable)
        elif isasyncgenfunction(callable) or isasyncgenfunction(getattr(callable, "__call__", None)):
            callable = asynccontextmanager(callable)

        self.target = ExecTarget(callable)


class DependDispatcher(BaseDispatcher):
    async def beforeExecution(self, interface: DispatcherInterface):
        interface.local_storage['_depend_lifespan_manager'] = AsyncExitStack()
        interface.local_storage['_depend_cached_results'] = {}
    
    async def catch(self, interface: DispatcherInterface):
        if not isinstance(interface.default, Depend):
            return
    
        dep = interface.default

        cache: dict = interface.local_storage['_depend_cached_results']
        if dep.raw in cache:
            return cache[dep.raw]
        
        result_tier1 = await interface.broadcast.Executor(
            target=dep.target,
            dispatchers=interface.dispatchers,
            depth=interface.depth + 1,
        )
        stack: AsyncExitStack = interface.local_storage['_depend_lifespan_manager']
        
        if isinstance(result_tier1, ContextManager):
            result = stack.enter_context(result_tier1)
            cache[dep.raw] = result
        elif isinstance(result_tier1, AsyncContextManager):
            result = await stack.enter_async_context(result_tier1)
            cache[dep.raw] = result
        else:
            result = result_tier1
            if dep.cache:
                cache[dep.raw] = result
        
        return Force(result)

    async def afterExecution(
        self,
        interface: DispatcherInterface,
        exception: Exception | None,
        tb: TracebackType | None,
    ):
        stack: AsyncExitStack = interface.local_storage['_depend_lifespan_manager']
        await stack.__aexit__(type(exception) if exception is not None else None, exception, tb)
