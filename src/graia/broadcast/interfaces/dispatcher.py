from functools import lru_cache
from inspect import getattr_static
from typing import TYPE_CHECKING, Any, Dict, Generic, Iterable, List, TypeVar

from ..entities.context import ExecutionContext, ParameterContext
from ..entities.dispatcher import BaseDispatcher
from ..entities.event import Dispatchable
from ..entities.signatures import Force
from ..exceptions import RequirementCrashed
from ..typing import DEFAULT_LIFECYCLE_NAMES, T_Dispatcher
from ..utilles import NestableIterable, run_always_await_safely

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
        d = getattr_static(dispatcher, name)
        h = getattr(d, "__func__", None)
        if h is not None and h not in LIFECYCLE_ABS:
            result[name] = getattr(dispatcher, name)
    return result


class DispatcherInterface(Generic[T_Event]):
    broadcast: "Broadcast"

    execution_contexts: List[ExecutionContext]
    parameter_contexts: List[ParameterContext]

    def __init__(self, broadcast_instance: "Broadcast") -> None:
        self.broadcast = broadcast_instance
        self.execution_contexts = []
        self.parameter_contexts = []

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
    def global_dispatcher(self) -> List[T_Dispatcher]:
        return self.broadcast.global_dispatchers

    def start_execution(
        self,
        dispatchers: List[T_Dispatcher],
    ):
        self.execution_contexts.append(ExecutionContext(dispatchers))
        self.flush_lifecycle_refs(dispatchers)
        return self

    def clean(self):
        self.execution_contexts.pop()

    def inject_execution_raw(self, *dispatchers: T_Dispatcher):
        for dispatcher in dispatchers:
            self.execution_contexts[-1].dispatchers.insert(0, dispatcher)

        self.flush_lifecycle_refs(dispatchers)

    def inject_global_raw(self, *dispatchers: T_Dispatcher):
        for dispatcher in dispatchers[::-1]:
            self.broadcast.global_dispatchers.insert(1, dispatcher)

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
            for k, v in result.items():
                lifecycle_refs[k].append(v)

    async def lookup_param(
        self,
        name: str,
        annotation: Any,
        default: Any,
        oplog: Any,
    ) -> Any:
        continued = 0
        self.parameter_contexts.append(ParameterContext(name, annotation, default))

        try:
            self.execution_contexts[-1].path = NestableIterable(oplog[0])
            for dispatcher in self.execution_contexts[-1].path:
                result = await getattr(dispatcher, "catch", dispatcher)(self)
                if result is None:  # 不可靠.
                    break
                if result.__class__ is Force:
                    return result.target
                return result
            oplog[0].clear()
            self.execution_contexts[-1].path = NestableIterable(self.execution_contexts[-1].dispatchers)
            for dispatcher in self.execution_contexts[-1].path:
                result = await getattr(dispatcher, "catch", dispatcher)(self)

                if result is None:
                    continued += 1
                    continue

                if result.__class__ is Force:
                    return result.target

                oplog[0].append(dispatcher)
                oplog[1] += continued
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

    async def lookup_by_directly(
        self, dispatcher: T_Dispatcher, name: str, annotation: Any, default: Any
    ) -> Any:
        self.parameter_contexts.append(
            ParameterContext(
                name,
                annotation,
                default,
            )
        )

        try:
            result = await getattr(dispatcher, "catch", dispatcher)(self)
            if result.__class__ is Force:
                return result.target

            return result
        finally:
            self.parameter_contexts.pop()
