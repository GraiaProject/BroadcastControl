import itertools
from functools import lru_cache, partial
from inspect import isclass, isfunction
from typing import (TYPE_CHECKING, Any, Dict, Generator, Generic, Iterable,
                    List, Optional, Sequence, TypeVar)

from graia.broadcast.cache import cached, hashkey
from graia.broadcast.entities.context import (LF_TEMPLATE, ExecutionContext,
                                              ParameterContext)
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.entities.signatures import Force
from graia.broadcast.entities.track_log import TrackLog, TrackLogType
from graia.broadcast.exceptions import RequirementCrashed
from graia.broadcast.typing import (DEFAULT_LIFECYCLE_NAMES, T_Dispatcher,
                                    T_Dispatcher_Callable)

from ..utilles import cached_getattr, run_always_await_safely

if TYPE_CHECKING:
    from graia.broadcast import Broadcast


class EmptyEvent(Dispatchable):
    class Dispatcher(BaseDispatcher):
        @staticmethod
        def catch(_):
            pass


T_Event = TypeVar("T_Event", bound=Dispatchable)


class DispatcherInterface(Generic[T_Event]):
    broadcast: "Broadcast"

    execution_contexts: List["ExecutionContext"]
    parameter_contexts: List["ParameterContext"]

    track_logs: List[TrackLog]

    @property
    def track_log(self):
        return self.track_logs[-1]

    @staticmethod
    @lru_cache(maxsize=None)
    def get_lifecycle_refs(dispatcher: "T_Dispatcher") -> List:
        return [
            cached_getattr(dispatcher, name, None) for name in DEFAULT_LIFECYCLE_NAMES
        ]

    def dispatcher_pure_generator(self) -> Iterable[T_Dispatcher]:
        return itertools.chain(
            self.execution_contexts[0].dispatchers,
            self.parameter_contexts[-1].dispatchers,
            self.execution_contexts[-1].dispatchers,
        )

    def flush_lifecycle_refs(
        self,
        dispatchers: Sequence["T_Dispatcher"] = None,
    ):
        from graia.broadcast.entities.dispatcher import BaseDispatcher

        lifecycle_refs = self.execution_contexts[-1].lifecycle_refs
        if dispatchers is None and lifecycle_refs != LF_TEMPLATE:
            return

        for dispatcher in dispatchers or self.dispatcher_pure_generator():
            if (
                not isinstance(dispatcher, BaseDispatcher)
                and dispatcher.__class__ is not type
            ):
                continue

            result = self.get_lifecycle_refs(dispatcher)
            for i in DEFAULT_LIFECYCLE_NAMES:
                v = result.pop(0)
                if v:
                    lifecycle_refs[i].append(v)

    async def exec_lifecycle(self, lifecycle_name: str, *args, **kwargs):
        lifecycle_funcs = self.execution_contexts[-1].lifecycle_refs.get(
            lifecycle_name, []
        )
        if lifecycle_funcs:
            for func in lifecycle_funcs:
                await run_always_await_safely(func, self, *args, **kwargs)

    def inject_local_raw(self, *dispatchers: "T_Dispatcher"):
        # 为什么没有 flush: 因为这里的 lifecycle 是无意义的.
        for dispatcher in dispatchers[::-1]:
            self.parameter_contexts[-1].dispatchers.insert(0, dispatcher)

    def inject_execution_raw(self, *dispatchers: "T_Dispatcher"):
        for dispatcher in dispatchers:
            self.execution_contexts[-1].dispatchers.insert(0, dispatcher)

        self.flush_lifecycle_refs(dispatchers)

    def inject_global_raw(self, *dispatchers: "T_Dispatcher"):
        # self.dispatchers.extend(dispatchers)
        for dispatcher in dispatchers[::-1]:
            self.execution_contexts[0].dispatchers.insert(1, dispatcher)

        self.flush_lifecycle_refs(dispatchers)

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
    def event(self) -> Dispatchable:
        return self.broadcast.event_ctx.get()

    @property
    def global_dispatcher(self) -> List[T_Dispatcher]:
        return self.execution_contexts[0].dispatchers

    @property
    def current_path(self) -> Iterable[T_Dispatcher]:
        return self.parameter_contexts[-1].path

    @property
    def has_current_exec_context(self) -> bool:
        return len(self.execution_contexts) >= 2

    @property
    def has_current_param_context(self) -> bool:
        return len(self.parameter_contexts) >= 2

    def __init__(self, broadcast_instance: "Broadcast") -> None:
        self.broadcast = broadcast_instance
        self.execution_contexts = [ExecutionContext([])]
        self.parameter_contexts = [
            ParameterContext(
                None,
                None,
                None,
                [],
                [
                    [],
                ],
            )
        ]
        self.track_logs = [TrackLog()]

    async def __aenter__(self) -> "DispatcherInterface":
        return self

    async def __aexit__(self, _, exc: Exception, tb):
        await self.exit_current_execution()
        if tb is not None:
            raise exc.with_traceback(tb)

    def start_execution(
        self,
        dispatchers: List[T_Dispatcher],
        track_log_receiver: TrackLog = None,
    ) -> "DispatcherInterface":
        self.execution_contexts.append(ExecutionContext(dispatchers))
        self.flush_lifecycle_refs()
        self.track_logs.append(track_log_receiver or TrackLog())
        return self

    async def exit_current_execution(self):
        self.execution_contexts.pop()
        self.track_logs.pop()

    @staticmethod
    @cached({}, hashkey)
    def dispatcher_callable_detector(dispatcher: T_Dispatcher) -> T_Dispatcher_Callable:
        if hasattr(dispatcher, "catch"):
            if isfunction(dispatcher.catch) or not isclass(dispatcher):
                return dispatcher.catch  # type: ignore
            else:
                return partial(dispatcher.catch, None)
        elif callable(dispatcher):
            return dispatcher
        else:
            raise ValueError("invaild dispatcher: ", dispatcher)

    def init_dispatch_path(self) -> List[List["T_Dispatcher"]]:
        return [
            [],
            self.execution_contexts[0].dispatchers,
            self.parameter_contexts[-1].dispatchers,
            self.execution_contexts[-1].dispatchers,
        ]

    async def lookup_param_without_log(
        self,
        name: str,
        annotation: Any,
        default: Any,
        using_path: List[List["T_Dispatcher"]] = None,
    ) -> Any:
        self.parameter_contexts.append(
            ParameterContext(
                name, annotation, default, [], using_path or self.init_dispatch_path()
            )
        )

        result = None
        try:
            for dispatcher in self.current_path:
                result = await run_always_await_safely(
                    self.dispatcher_callable_detector(dispatcher), self
                )

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
            self.parameter_contexts.pop()

    async def lookup_param(
        self,
        name: str,
        annotation: Any,
        default: Any,
        using_path: List[List["T_Dispatcher"]] = None,
    ) -> Any:
        self.parameter_contexts.append(
            ParameterContext(
                name, annotation, default, [], using_path or self.init_dispatch_path()
            )
        )
        track_log = self.track_log.log

        track_log.append((TrackLogType.LookupStart, name, annotation, default))
        try:
            for dispatcher in self.current_path:
                result = await run_always_await_safely(
                    self.dispatcher_callable_detector(dispatcher), self
                )

                if result is None:
                    self.track_log.fluent_success = False
                    track_log.append((TrackLogType.Continue, name, dispatcher))
                    continue

                if result.__class__ is Force:
                    result = result.target

                track_log.append((TrackLogType.Result, name, dispatcher))
                self.execution_contexts[-1]._index = 0
                return result
            else:
                track_log.append((TrackLogType.RequirementCrashed, name))
                raise RequirementCrashed(
                    "the dispatching requirement crashed: ",
                    self.name,
                    self.annotation,
                    self.default,
                )
        finally:
            track_log.append((TrackLogType.LookupEnd, name))
            self.parameter_contexts.pop()

    async def lookup_using_current(self) -> Any:
        result = None
        for dispatcher in self.current_path:
            result = await run_always_await_safely(
                self.dispatcher_callable_detector(dispatcher), self
            )
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

    async def lookup_by_directly(
        self,
        dispatcher: T_Dispatcher,
        name: str,
        annotation: Any,
        default: Any,
        using_path: List[List["T_Dispatcher"]] = None,
    ) -> Any:
        self.parameter_contexts.append(
            ParameterContext(
                name, annotation, default, [], using_path or self.init_dispatch_path()
            )
        )

        dispatcher_callable = self.dispatcher_callable_detector(dispatcher)

        try:
            result = await run_always_await_safely(dispatcher_callable, self)
            if result.__class__ is Force:
                return result.target

            return result
        finally:
            self.parameter_contexts.pop()
