from typing import TYPE_CHECKING, Any, Generic, List, Tuple, TypeVar

from ..entities.context import ExecutionContext
from ..entities.dispatcher import BaseDispatcher
from ..entities.event import Dispatchable
from ..entities.signatures import Force
from ..exceptions import RequirementCrashed
from ..typing import T_Dispatcher
from ..utilles import NestableIterable

if TYPE_CHECKING:
    from .. import Broadcast


class EmptyEvent(Dispatchable):
    class Dispatcher(BaseDispatcher):
        @staticmethod
        def catch(_):
            pass


T_Event = TypeVar("T_Event", bound=Dispatchable)


class DispatcherInterface(Generic[T_Event]):
    broadcast: "Broadcast"

    execution_contexts: List[ExecutionContext]
    parameter_contexts: List[Tuple[str, Any, Any]]

    def __init__(self, broadcast_instance: "Broadcast") -> None:
        self.broadcast = broadcast_instance
        self.execution_contexts = []
        self.parameter_contexts = []

    @property
    def name(self) -> str:
        return self.parameter_contexts[-1][0]

    @property
    def annotation(self) -> Any:
        return self.parameter_contexts[-1][1]

    @property
    def default(self) -> Any:
        return self.parameter_contexts[-1][2]

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
        self.execution_contexts[-1].path = NestableIterable([])
        return self

    def clean(self):
        self.execution_contexts.pop()

    def inject_execution_raw(self, *dispatchers: T_Dispatcher):
        for dispatcher in dispatchers:
            self.execution_contexts[-1].dispatchers.insert(0, dispatcher)

    def inject_global_raw(self, *dispatchers: T_Dispatcher):
        for dispatcher in dispatchers[::-1]:
            self.broadcast.global_dispatchers.insert(1, dispatcher)

    async def lookup_param(
        self,
        name: str,
        annotation: Any,
        default: Any,
        optimized_log: Any,
    ) -> Any:
        self.parameter_contexts.append((name, annotation, default))
        dispatch_path = self.execution_contexts[-1].path

        try:
            dispatch_path.iterable = optimized_log
            for dispatcher in dispatch_path:
                result = await getattr(dispatcher, "catch", dispatcher)(self)  # type: ignore
                if result is None:  # 不可靠.
                    break
                if result.__class__ is Force:
                    return result.target
                return result
            optimized_log.clear()
            dispatch_path.iterable = self.execution_contexts[-1].dispatchers
            for dispatcher in dispatch_path:
                result = await getattr(dispatcher, "catch", dispatcher)(self)  # type: ignore

                if result is None:
                    continue

                if result.__class__ is Force:
                    return result.target

                optimized_log.append(dispatcher)
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

    async def lookup_by_directly(self, dispatcher: T_Dispatcher, name: str, annotation: Any, default: Any) -> Any:
        self.parameter_contexts.append((name, annotation, default))

        try:
            result = await getattr(dispatcher, "catch", dispatcher)(self)  # type: ignore
            if result.__class__ is Force:
                return result.target

            return result
        finally:
            self.parameter_contexts.pop()
