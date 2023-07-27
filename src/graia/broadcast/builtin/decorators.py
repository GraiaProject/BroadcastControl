import typing
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    AsyncExitStack,
    asynccontextmanager,
    contextmanager,
)
from inspect import isasyncgenfunction, isgeneratorfunction
from typing import Any, Callable, Optional, Union

from ..entities.decorator import Decorator
from ..entities.exectarget import ExecTarget
from ..entities.signatures import Force
from ..exceptions import RequirementCrashed
from ..interfaces.decorator import DecoratorInterface


class Depend(Decorator):
    pre = True
    depend_callable: ExecTarget
    cache: bool = False

    def __init__(self, callable: Callable, *, cache=False):
        self.cache = cache
        if isgeneratorfunction(callable) or isgeneratorfunction(getattr(callable, "__call__", None)):
            callable = contextmanager(callable)
            self._target = self._generator_target
        elif isasyncgenfunction(callable) or isasyncgenfunction(getattr(callable, "__call__", None)):
            callable = asynccontextmanager(callable)
            self._target = self._asyncgen_target
        self.depend_callable = ExecTarget(callable)

    def __repr__(self) -> str:
        return "<Depend target={0}>".format(self.depend_callable)

    async def target(self, interface: DecoratorInterface):
        if self.cache:
            attempt = interface.local_storage.get(self.depend_callable)  # type: ignore
            if attempt:
                return Force(attempt)

        result = await interface.dispatcher_interface.broadcast.Executor(
            target=self.depend_callable,
            dispatchers=interface.dispatcher_interface.dispatchers,
            depth=interface.dispatcher_interface.depth + 1,
        )

        result = await self._target(interface, result)

        if self.cache:
            interface.local_storage[self.depend_callable] = result  # type: ignore
        return Force(result)

    @staticmethod
    async def _target(_, result: Any):
        return result

    @staticmethod
    async def _generator_target(interface: DecoratorInterface, result: AbstractContextManager):
        if (stack := interface.local_storage.get("_depend_astack")) is None:
            stack = interface.local_storage["_depend_astack"] = AsyncExitStack()

        return stack.enter_context(result)

    @staticmethod
    async def _asyncgen_target(interface: DecoratorInterface, result: AbstractAsyncContextManager):
        if (stack := interface.local_storage.get("_depend_astack")) is None:
            stack = interface.local_storage["_depend_astack"] = AsyncExitStack()

        return await stack.enter_async_context(result)


class OptionalParam(Decorator):
    pre = True

    def __init__(self, origin: Any):
        self.origin = origin

    async def target(self, interface: DecoratorInterface) -> Optional[Any]:
        annotation = interface.annotation
        if typing.get_origin(annotation) is Union:
            annotation = Union[tuple(x for x in typing.get_args(annotation) if x not in (None, type(None)))]  # type: ignore
        try:
            return Force(
                await interface.dispatcher_interface.lookup_by_directly(
                    interface,
                    interface.dispatcher_interface.name,
                    annotation,
                    self.origin,
                )
            )
        except RequirementCrashed:
            return Force()
