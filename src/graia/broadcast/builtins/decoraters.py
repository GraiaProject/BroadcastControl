from ..entities.decorater import Decorater
from ..protocols.executor import ExecutorProtocol
from typing import Callable, ContextManager
from ..entities.signatures import Force
from ..interfaces.decorater import DecoraterInterface
import inspect
from ..exceptions import InvaildContextTarget

class Depend(Decorater):
    pre = True
    depend_callable: Callable
    cache: bool = False

    def __init__(self, callable, *, cache=False):
        self.cache = cache
        self.depend_callable = callable

    async def target(self, interface: DecoraterInterface):
        if self.cache:
            if interface.local_storage.get(self.depend_callable):
                return interface.local_storage.get(self.depend_callable)
        result = Force(await interface.dispatcher_interface.broadcast.Executor(ExecutorProtocol(
            target=self.depend_callable,
            event=interface.event,
            hasReferrer=True
        )))
        if self.cache:
            interface.local_storage[self.depend_callable] = result
        return result

class Middleware(Decorater):
    pre = True
    context_target: ContextManager

    def __init__(self, context_target: ContextManager):
        self.context_target = context_target

    async def target(self, interface: DecoraterInterface):
        if all([
            hasattr(self.context_target, "__aenter__"),
            hasattr(self.context_target, "__aexit__")
        ]):
            async with self.context_target as mw_value:
                yield mw_value
        elif all([
            hasattr(self.context_target, "__enter__"),
            hasattr(self.context_target, "__exit__")
        ]):
            with self.context_target as mw_value:
                yield mw_value
        else:
            raise InvaildContextTarget(self.context_target, "is not vaild as a context target.")