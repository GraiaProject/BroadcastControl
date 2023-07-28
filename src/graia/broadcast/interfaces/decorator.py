from contextlib import AsyncExitStack
from types import TracebackType
from typing import TYPE_CHECKING, Optional, cast

from ..entities.decorator import Decorator
from ..entities.dispatcher import BaseDispatcher
from ..entities.signatures import Force
from ..utilles import Ctx, run_always_await

if TYPE_CHECKING:
    from ..interfaces.dispatcher import DispatcherInterface


ctx_dei_returnvalue = Ctx("ctx_dei_returnvalue")


class DecoratorInterface(BaseDispatcher):
    """Broadcast Control 内部机制 Decorator 的具体管理实现"""

    @property
    def dispatcher_interface(self) -> "DispatcherInterface":
        from .dispatcher import DispatcherInterface

        return DispatcherInterface.ctx.get()

    @property
    def name(self):
        return self.dispatcher_interface.name

    @property
    def annotation(self):
        return self.dispatcher_interface.annotation

    @property
    def event(self):
        return self.dispatcher_interface.event

    @property
    def return_value(self):
        return ctx_dei_returnvalue.get()

    @property
    def local_storage(self):
        return self.dispatcher_interface.local_storage

    async def catch(self, interface: "DispatcherInterface"):
        if isinstance(interface.default, Decorator):
            decorator: Decorator = interface.default
            with ctx_dei_returnvalue.use(
                await interface.lookup_param(interface.name, interface.annotation, None) if not decorator.pre else None
            ):
                return Force(await run_always_await(decorator.target, self))

    async def afterExecution(
        self, interface: "DispatcherInterface", exception: Optional[Exception], tb: Optional[TracebackType]
    ):
        stack = cast("AsyncExitStack | None", interface.local_storage.get("_depend_astack"))

        if stack is None:
            return

        if exception:
            await stack.__aexit__(type(exception), exception, tb)
        else:
            await stack.aclose()
