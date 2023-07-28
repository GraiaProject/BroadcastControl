from asyncio import Future
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Generic,
    List,
    Set,
    Tuple,
    TypeVar,
    Union,
)

from ..entities.event import Dispatchable
from ..entities.signatures import Force
from ..exceptions import ExecutionStop, RequirementCrashed
from ..typing import T_Dispatcher
from ..utilles import Ctx, NestableIterable

try:
    from typing_extensions import get_args, get_origin
except ImportError:
    from typing import get_args, get_origin

try:
    from typing_extensions import Annotated
except ImportError:
    from typing import Annotated

if TYPE_CHECKING:
    from .. import Broadcast


T_Event = TypeVar("T_Event", bound=Dispatchable, covariant=True)


class DispatcherInterface(Generic[T_Event]):
    __slots__ = {
        "broadcast",
        "dispatchers",
        "parameter_contexts",
        "local_storage",
        "current_path",
        "current_oplog",
        "success",
        "_depth",
        "exec_result",
    }

    ctx: "ClassVar[Ctx[DispatcherInterface]]" = Ctx("bcc_dii")
    exec_result: "Future[Any]"

    broadcast: "Broadcast"
    dispatchers: List[T_Dispatcher]
    local_storage: Dict[str, Any]
    current_path: NestableIterable[T_Dispatcher]
    current_oplog: List[T_Dispatcher]

    parameter_contexts: List[Tuple[str, Any, Any]]
    success: Set[str]
    _depth: int

    def __init__(self, broadcast_instance: "Broadcast", dispatchers: List[T_Dispatcher], depth: int = 0) -> None:
        self.broadcast = broadcast_instance
        self.dispatchers = dispatchers
        self.parameter_contexts = []
        self.local_storage = {}
        self.current_path = NestableIterable([])
        self.current_oplog = []
        self.success = set()
        self.exec_result = Future()
        self._depth = depth

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
    def is_optional(self) -> bool:
        anno = self.annotation
        return get_origin(anno) is Union and type(None) in get_args(anno)

    @property
    def is_annotated(self) -> bool:
        return get_origin(self.annotation) is Annotated

    @property
    def annotated_origin(self) -> Any:
        if not self.is_annotated:
            raise TypeError("required a annotated annotation")
        return get_args(self.annotation)[0]

    @property
    def annotated_metadata(self) -> tuple:
        if not self.is_annotated:
            raise TypeError("required a annotated annotation")
        return get_args(self.annotation)[1:]

    @property
    def depth(self) -> int:
        return self._depth

    def inject_execution_raw(self, *dispatchers: T_Dispatcher):
        for dispatcher in dispatchers:
            self.dispatchers.insert(0, dispatcher)

    def crash(self):
        raise RequirementCrashed(
            self.name,
            self.annotation,
            self.default,
        )

    def stop(self):
        raise ExecutionStop

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
                    result = await dispatcher.catch(self)  # type: ignore
                    if result is None:  # 不可靠.
                        break
                    self.success.add(name)
                    if result.__class__ is Force:
                        return result.target
                    return result
                oplog.clear()
            self.current_path.iterable = self.dispatchers
            for dispatcher in self.current_path:
                result = await dispatcher.catch(self)  # type: ignore

                if result is None:
                    continue

                oplog.insert(0, dispatcher)

                if result.__class__ is Force:
                    return result.target

                return result
            raise RequirementCrashed(
                self.name,
                self.annotation,
                self.default,
            )
        finally:
            self.parameter_contexts.pop()

    async def lookup_by_directly(self, dispatcher: T_Dispatcher, name: str, annotation: Any, default: Any) -> Any:
        self.parameter_contexts.append((name, annotation, default))

        try:
            result = await dispatcher.catch(self)  # type: ignore
            if result.__class__ is Force:
                return result.target

            return result
        finally:
            self.parameter_contexts.pop()
