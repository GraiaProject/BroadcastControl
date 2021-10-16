from functools import lru_cache
from inspect import getattr_static
from itertools import chain
from types import MethodType
from typing import TYPE_CHECKING, Any, Dict, Generic, Iterable, List, TypeVar

from ..entities.context import ExecutionContext, ParameterContext
from ..entities.dispatcher import BaseDispatcher
from ..entities.event import Dispatchable
from ..entities.signatures import Force
from ..entities.track_log import TrackLog, TrackLogType
from ..exceptions import RequirementCrashed
<<<<<<< HEAD
from ..typing import DEFAULT_LIFECYCLE_NAMES, T_Dispatcher
=======
from ..typing import DEFAULT_LIFECYCLE_NAMES, T_Dispatcher, T_Dispatcher_Callable
>>>>>>> 96d22dae550554c5acaff687150adb571e603fba
from ..utilles import run_always_await_safely

if TYPE_CHECKING:
    from .. import Broadcast


class EmptyEvent(Dispatchable):
    class Dispatcher(BaseDispatcher):
        @staticmethod
        def catch(_):
            pass


T_Event = TypeVar("T_Event", bound=Dispatchable)

LIFECYCLE_ABS = {
    BaseDispatcher.beforeExecution,
    BaseDispatcher.afterDispatch,
    BaseDispatcher.afterExecution,
}


@lru_cache(maxsize=None)
def get_lifecycle_refs(dispatcher: T_Dispatcher) -> Dict:
    result = {}

    for name in DEFAULT_LIFECYCLE_NAMES:
        v = getattr(dispatcher, name, None)
        if not v:
            continue
        d = getattr_static(dispatcher, name, None)
        if (
            isinstance(d, (staticmethod, MethodType))
            and d.__func__ not in LIFECYCLE_ABS
        ):
            result[name] = v
    return result


class DispatcherInterface(Generic[T_Event]):
    broadcast: "Broadcast"

    execution_contexts: List[ExecutionContext]
    parameter_contexts: List[ParameterContext]

    track_logs: List[TrackLog]

    def __init__(self, broadcast_instance: "Broadcast") -> None:
        self.broadcast = broadcast_instance
        self.execution_contexts = [ExecutionContext([])]
        self.parameter_contexts = [ParameterContext(None, None, None, [[]])]
        self.track_logs = [TrackLog()]

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
    def event(self) -> T_Event:
        return self.broadcast.event_ctx.get()  # type: ignore

    @property
    def track_log(self) -> TrackLog:
        return self.track_logs[-1]

    @property
    def global_dispatcher(self) -> List[T_Dispatcher]:
        return self.execution_contexts[0].dispatchers

    @property
    def current_path(self):
        return self.parameter_contexts[-1].path

    def start_execution(
        self,
        dispatchers: List[T_Dispatcher],
        track_log_receiver: TrackLog,
    ):
        self.execution_contexts.append(ExecutionContext(dispatchers))
        self.track_logs.append(track_log_receiver)
        self.flush_lifecycle_refs(chain(*self.dispatcher_pure_generator()))
        return self

    def clean(self):
        self.execution_contexts.pop()
        self.track_logs.pop()

    def dispatcher_pure_generator(self) -> List[List[T_Dispatcher]]:
        return [
            self.execution_contexts[0].dispatchers,
            self.execution_contexts[-1].dispatchers,
        ]

    def inject_execution_raw(self, *dispatchers: T_Dispatcher):
        for dispatcher in dispatchers:
            self.execution_contexts[-1].dispatchers.insert(0, dispatcher)

        self.flush_lifecycle_refs(dispatchers)

    def inject_global_raw(self, *dispatchers: T_Dispatcher):
        for dispatcher in dispatchers[::-1]:
            self.execution_contexts[0].dispatchers.insert(1, dispatcher)

        self.flush_lifecycle_refs(dispatchers)

    async def exec_lifecycle(self, lifecycle_name: str, *args, **kwargs):
        lifecycle_funcs = self.execution_contexts[-1].lifecycle_refs.get(lifecycle_name)
        if lifecycle_funcs:
            for func in lifecycle_funcs:
                await run_always_await_safely(func, self, *args, **kwargs)

    def flush_lifecycle_refs(
        self,
        dispatchers: Iterable[T_Dispatcher],
    ):
        lifecycle_refs = self.execution_contexts[-1].lifecycle_refs

        for dispatcher in dispatchers:
            if dispatcher.__class__ is not type and not isinstance(
                dispatcher, BaseDispatcher
            ):
                continue

            result = get_lifecycle_refs(dispatcher)
            if result:
                for k, v in result.items():
                    lifecycle_refs[k].append(v)

    async def lookup_param_without_log(
        self,
        name: str,
        annotation: Any,
        default: Any,
        using_path: List[List[T_Dispatcher]],
    ) -> Any:
        self.parameter_contexts.append(
            ParameterContext(name, annotation, default, using_path)
        )

        try:
            for dispatcher in self.current_path:
                result = await getattr(dispatcher, "catch", dispatcher)(self)

                if result is None:
                    continue

                if result.__class__ is Force:
                    return result.target

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
        using_path: List[List[T_Dispatcher]] = None,
    ) -> Any:
        self.parameter_contexts.append(
            ParameterContext(
                name,
                annotation,
                default,
                using_path or self.dispatcher_pure_generator(),
            )
        )
        track_log = self.track_log.log

        track_log.append((TrackLogType.LookupStart, name, annotation, default))
        try:
            for dispatcher in self.current_path:
                result = await getattr(dispatcher, "catch", dispatcher)(self)

                if result is None:
                    self.track_log.fluent_success = False
                    track_log.append((TrackLogType.Continue, name, dispatcher))
                    continue

                if result.__class__ is Force:
                    return result.target

                track_log.append((TrackLogType.Result, name, dispatcher))
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
        for dispatcher in self.current_path:
            result = await getattr(dispatcher, "catch", dispatcher)(self)
            if result is None:
                continue

            if result.__class__ is Force:
                return result.target

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
        using_path: List[List[T_Dispatcher]] = None,
    ) -> Any:
        self.parameter_contexts.append(
            ParameterContext(
                name,
                annotation,
                default,
                using_path or self.dispatcher_pure_generator(),
            )
        )

        try:
            result = await getattr(dispatcher, "catch", dispatcher)(self)
            if result.__class__ is Force:
                return result.target

            return result
        finally:
            self.parameter_contexts.pop()
