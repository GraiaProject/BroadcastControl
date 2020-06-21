from .dispatcher import DispatcherInterface
from ..entities.decorater import Decorater
from ..entities.signatures import Force
from ..utilles import run_always_await
from typing import Dict, Any
import inspect

class DecoraterInterface:
    """Graia Broadcast Control 内部机制 Decorate 的具体管理实现
    """
    dispatcher_interface: DispatcherInterface
    local_storage: Dict[str, Any] = {}
    return_value: Any = None

    def __init__(self, dispatcher_interface: DispatcherInterface):
        self.dispatcher_interface = dispatcher_interface
        self.dispatcher_interface.dispatchers.insert(0, self.decorater_dispatcher)

    @property
    def name(self):
        return self.dispatcher_interface.name

    @property
    def annotation(self):
        return self.dispatcher_interface.annotation

    @property
    def default(self):
        return

    @property
    def event(self):
        return self.dispatcher_interface.event

    async def decorater_dispatcher(self, interface: DispatcherInterface):
        if isinstance(interface.default, Decorater):
            decorater: Decorater = interface.default
            if not decorater.pre:
                # 作为 装饰
                self.return_value = await interface.execute_with(interface.name, interface.annotation, None)
                try:
                    # 这里隐式的复用了 dispatcher interface 的生成器终结者机制
                    if inspect.isasyncgenfunction(decorater.target):
                        # 如果是异步生成器
                        async for i in decorater.target(self):
                            yield i
                    elif (inspect.isgeneratorfunction(decorater.target) and \
                        not inspect.iscoroutinefunction(decorater.target)):
                        # 同步生成器
                        for i in decorater.target(self):
                            yield i
                    else:
                        yield Force(await run_always_await(decorater.target(self)))
                finally:
                    self.return_value = None
            else:
                yield Force(await run_always_await(decorater.target(self)))