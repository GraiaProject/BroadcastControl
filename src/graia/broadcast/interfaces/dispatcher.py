from inspect import isclass, isfunction, ismethod
import inspect
import traceback
import weakref
import itertools
from functools import lru_cache, partial

from graia.broadcast.abstract.interfaces.dispatcher import IDispatcherInterface
from typing import (
    Any,
    Callable,
    Generator,
    Iterator,
    List,
    Optional,
    TYPE_CHECKING,
    Tuple,
    Type,
    Union,
)
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import BaseEvent

from graia.broadcast.entities.context import ExecutionContext, ParameterContext
from graia.broadcast.entities.signatures import Force
from graia.broadcast.entities.source import DispatcherSource
from graia.broadcast.exceptions import OutOfMaxGenerater, RequirementCrashed
from graia.broadcast.typing import T_Dispatcher, T_Dispatcher_Callable

from ..utilles import NestableIterable, run_always_await_safely

if TYPE_CHECKING:
    from graia.broadcast import Broadcast


class EmptyEvent(BaseEvent):
    class Dispatcher(BaseDispatcher):
        @staticmethod
        def catch(_):
            pass


class DispatcherInterface(IDispatcherInterface):
    nestable_iter: NestableIterable[
        Tuple[T_Dispatcher, T_Dispatcher_Callable, DispatcherSource]
    ] = None

    @property
    def name(self) -> str:
        return self.parameter_contexts[-1].name

    @property
    def annotation(self) -> Any:
        return self.parameter_contexts[-1].annotation

    @property
    def default(self) -> Any:
        return self.parameter_contexts[-1].default

    @property
    def _index(self) -> int:
        return self.execution_contexts[-1]._index

    @property
    def event(self) -> BaseEvent:
        return self.execution_contexts[-1].event

    @property
    def global_dispatcher(self) -> List[T_Dispatcher]:
        return self.execution_contexts[0].dispatchers

    @property
    def has_current_exec_context(self) -> bool:
        return len(self.execution_contexts) >= 2

    @property
    def has_current_param_context(self) -> bool:
        return len(self.parameter_contexts) >= 2

    def __init__(self, broadcast_instance: "Broadcast") -> None:
        self.broadcast = broadcast_instance
        self.execution_contexts = [ExecutionContext([], EmptyEvent())]
        self.parameter_contexts = [ParameterContext(None, None, None, [])]

    async def __aenter__(self) -> "DispatcherInterface":
        return self

    async def __aexit__(self, _, exc: Exception, tb):
        await self.exit_current_execution()
        if tb is not None:
            raise exc.with_traceback(tb)

    def start_execution(
        self,
        event: BaseEvent,
        dispatchers: List[T_Dispatcher],
    ) -> "DispatcherInterface":
        self.execution_contexts.append(ExecutionContext(dispatchers, event))
        self.nestable_iter = NestableIterable(list(self.dispatcher_generator()))
        self.flush_lifecycle_refs()
        return self

    async def exit_current_execution(self):
        self.execution_contexts.pop()
        self.nestable_iter = None

    @property
    def dispatcher_sources(self) -> List[DispatcherSource]:
        return [
            self.execution_contexts[0].source,
            self.parameter_contexts[-1].source,
            self.execution_contexts[-1].source,
        ]

    def dispatcher_pure_generator(self) -> Generator[None, None, T_Dispatcher]:
        for source in self.dispatcher_sources:
            yield from source.dispatchers

    @staticmethod
    @lru_cache(None)
    def dispatcher_callable_detector(dispatcher: T_Dispatcher) -> T_Dispatcher_Callable:
        if hasattr(dispatcher, "catch"):
            if isfunction(dispatcher.catch) or not isclass(dispatcher):
                return dispatcher.catch
            else:
                return partial(dispatcher.catch, None)
        elif callable(dispatcher):
            return dispatcher
        else:
            raise ValueError("invaild dispatcher: ", dispatcher)

    def dispatcher_generator(
        self,
        source_from: Iterator[DispatcherSource[T_Dispatcher, Any]] = None,
        using_always: bool = True,
    ) -> Generator[
        None, None, Tuple[T_Dispatcher, T_Dispatcher_Callable, DispatcherSource]
    ]:
        always_dispatcher = self.execution_contexts[-1].always_dispatchers
        if source_from is None:
            source_from = self.dispatcher_sources

        for source in source_from:
            for dispatcher in source.dispatchers:
                if using_always and dispatcher in always_dispatcher:
                    always_dispatcher.remove(dispatcher)

                dispatcher_callable = self.dispatcher_callable_detector(dispatcher)
                yield (dispatcher, dispatcher_callable, source)

    async def lookup_param(
        self, name: str, annotation: Any, default: Any
    ) -> Union[Any, Tuple[Any, T_Dispatcher, DispatcherSource, List[T_Dispatcher]]]:
        self.parameter_contexts.append(ParameterContext(name, annotation, default, []))

        result = None
        try:
            for dispatcher, dispatcher_callable, source in self.nestable_iter:
                result = await run_always_await_safely(dispatcher_callable, self)

                if result is None:
                    continue

                if result.__class__ is Force:
                    result = result.target

                self.execution_contexts[-1]._index = 0
                return result
            else:
                raise RequirementCrashed(
                    "the dispatching requirement crashed: ",
                    self.name,
                    self.annotation,
                    self.default,
                )
        finally:
            always_dispatchers = self.execution_contexts[-1].always_dispatchers
            if always_dispatchers:
                for (
                    dispatcher,
                    dispatcher_callable,
                    source,
                ) in self.dispatcher_generator(
                    [DispatcherSource(always_dispatchers)],
                    using_always=False,
                ):
                    await run_always_await_safely(dispatcher_callable, self)

            self.parameter_contexts.pop()

    async def lookup_using_current(self) -> Any:
        result = None
        try:
            for dispatcher, dispatcher_callable, source in self.nestable_iter:
                result = await run_always_await_safely(dispatcher_callable, self)

                if result is None:
                    continue

                if result.__class__ is Force:
                    result = result.target

                self.execution_contexts[-1]._index = 0
                return result
            else:
                raise RequirementCrashed(
                    "the dispatching requirement crashed: ",
                    self.name,
                    self.annotation,
                    self.default,
                )
        finally:
            for dispatcher, dispatcher_callable, source in self.dispatcher_generator(
                [DispatcherSource(self.execution_contexts[-1].always_dispatchers)],
                using_always=False,
            ):
                await run_always_await_safely(dispatcher_callable, self)

    async def lookup_by_directly(
        self, dispatcher: T_Dispatcher, name: str, annotation: Any, default: Any
    ) -> Any:
        self.parameter_contexts.append(ParameterContext(name, annotation, default, []))

        dispatcher_callable = self.dispatcher_callable_detector(dispatcher)

        try:
            result = await run_always_await_safely(dispatcher_callable, self)
            if result.__class__ is Force:
                return result.target

            return result
        finally:
            self.parameter_contexts.pop()
