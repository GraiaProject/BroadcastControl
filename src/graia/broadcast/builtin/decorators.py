from graia.broadcast.entities.exectarget import ExecTarget
from ..entities.decorator import Decorator
from ..entities.signatures import Force
from ..interfaces.decorator import DecoratorInterface


class Depend(Decorator):
    pre = True
    depend_callable: ExecTarget
    cache: bool = False

    def __init__(self, callable, *, cache=False):
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
            event=interface.event,
            post_exception_event=True,
        )

        if self.cache:
            interface.local_storage[self.depend_callable] = result
        return Force(result)
