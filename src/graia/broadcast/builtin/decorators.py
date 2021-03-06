from ..entities.decorator import Decorator
from typing import Callable, ContextManager, Any, Hashable
from ..entities.signatures import Force
from ..interfaces.decorator import DecoratorInterface
import inspect
from ..exceptions import InvaildContextTarget


class Depend(Decorator):
    pre = True
    depend_callable: Callable
    cache: bool = False

    def __init__(self, callable, *, cache=False):
        self.cache = cache
        self.depend_callable = callable

    def __repr__(self) -> str:
        return "<Depend target={0}>".format(self.depend_callable)

    async def target(self, interface: DecoratorInterface):
        if self.cache:
            attempt = interface.local_storage.get(self.depend_callable)
            if attempt:
                return Force(attempt)
        result = await interface.dispatcher_interface.broadcast.Executor(
            target=self.depend_callable,
            event=interface.event,
            post_exception_event=True,
        )

        if self.cache:
            interface.local_storage[self.depend_callable] = result
        return Force(result)


class Middleware(Decorator):  # TODO: use lifecycle...?
    pre = True
    context_target: Any

    def __init__(self, context_target: ContextManager):
        self.context_target = context_target

    async def target(self, interface: DecoratorInterface):
        if all(
            [
                hasattr(self.context_target, "__aenter__"),
                hasattr(self.context_target, "__aexit__"),
            ]
        ):
            async with self.context_target as mw_value:
                yield mw_value
        elif all(
            [
                hasattr(self.context_target, "__enter__"),
                hasattr(self.context_target, "__exit__"),
            ]
        ):
            with self.context_target as mw_value:
                yield mw_value
        else:
            raise InvaildContextTarget(
                self.context_target, "is not vaild as a context target."
            )
