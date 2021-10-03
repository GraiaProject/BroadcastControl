import typing
from typing import Any, Callable, Optional

from ..entities.decorator import Decorator
from ..entities.exectarget import ExecTarget
from ..entities.signatures import Force
from ..exceptions import RequirementCrashed
from ..interfaces.decorator import DecoratorInterface
from ..utilles import dispatcher_mixin_handler


class Depend(Decorator):
    pre = True
    depend_callable: ExecTarget
    cache: bool = False

    def __init__(self, callable: Callable, *, cache=False):
        self.cache = cache
        self.depend_callable = ExecTarget(callable)

    def __repr__(self) -> str:
        return "<Depend target={0}>".format(self.depend_callable)

    async def target(self, interface: DecoratorInterface):
        if self.cache:
            attempt = interface.local_storage.get(self.depend_callable)
            if attempt:
                return Force(attempt)
        result = await interface.dispatcher_interface.broadcast.Executor(
            target=self.depend_callable,
            dispatchers=dispatcher_mixin_handler(interface.event.Dispatcher),
        )

        if self.cache:
            interface.local_storage[self.depend_callable] = result
        return Force(result)


class OptionalParam(Decorator):
    pre = True

    def __init__(self, origin: Any):
        self.origin = origin

    async def target(self, interface: DecoratorInterface) -> Optional[Any]:
        try:
            return Force(
                await interface.dispatcher_interface.lookup_param(
                    interface.dispatcher_interface.name,
                    interface.dispatcher_interface.annotation.__args__[0]
                    if isinstance(
                        interface.dispatcher_interface.annotation, typing._GenericAlias  # type: ignore
                    )
                    and type(None) in interface.dispatcher_interface.annotation.__args__
                    else interface.dispatcher_interface.annotation,
                    self.origin,
                )
            )
        except RequirementCrashed:
            return Force()
