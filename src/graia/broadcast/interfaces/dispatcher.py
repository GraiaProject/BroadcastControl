from typing import (TYPE_CHECKING, Any, ClassVar, Dict, Generic, List,
                    Optional, Tuple, TypeVar)

from ..entities.dispatcher import BaseDispatcher
from ..entities.event import Dispatchable
from ..entities.signatures import Force
from ..exceptions import RequirementCrashed
from ..typing import T_Dispatcher
from ..utilles import Ctx, NestableIterable

if TYPE_CHECKING:
    from .. import Broadcast


T_Event = TypeVar("T_Event", bound=Dispatchable)


class DispatcherInterface(Generic[T_Event]):
    __slots__ = {"broadcast", "dispatchers", "parameter_contexts", "local_storage", "current_path", "current_oplog"}

    ctx: "ClassVar[Ctx[DispatcherInterface]]" = Ctx("bcc_dii")

    broadcast: "Broadcast"
    dispatchers: List[T_Dispatcher]
    local_storage: Dict[str, Any]
    current_path: NestableIterable[T_Dispatcher]
    current_oplog: List[T_Dispatcher]

    parameter_contexts: List[Tuple[str, Any, Any]]

    def __init__(self, broadcast_instance: "Broadcast", dispatchers: List[T_Dispatcher]) -> None:
        self.broadcast = broadcast_instance
        self.dispatchers = dispatchers
        self.parameter_contexts = []
        self.local_storage = {}
        self.current_path = NestableIterable([])
        self.current_oplog = []

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

    def inject_execution_raw(self, *dispatchers: T_Dispatcher):
        for dispatcher in dispatchers:
            self.dispatchers.insert(0, dispatcher)

    async def lookup_param(
        self,
        name: str,
        annotation: Any,
        default: Any,
    ) -> Any:
        self.parameter_contexts.append((name, annotation, default))
        oplog = self.current_oplog

        try:
            if oplog:
                self.current_path.iterable = oplog
                for dispatcher in self.current_path:
                    result = await dispatcher.catch(self)
                    if result is None:  # 不可靠.
                        break
                    if result.__class__ is Force:
                        return result.target
                    return result
            oplog.clear()
            self.current_path.iterable = self.dispatchers
            for dispatcher in self.current_path:
                result = await dispatcher.catch(self)

                if result is None:
                    continue

                if result.__class__ is Force:
                    return result.target

                oplog.append(dispatcher)
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
            result = await dispatcher.catch(self)
            if result.__class__ is Force:
                return result.target

            return result
        finally:
            self.parameter_contexts.pop()
