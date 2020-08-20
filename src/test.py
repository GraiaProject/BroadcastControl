from graia.broadcast.entities.event import BaseEvent
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.protocols.executor import ExecutorProtocol
from graia.broadcast.entities.listener import Listener
from graia.broadcast import Broadcast
from graia.broadcast.entities.decorater import Decorater
from graia.broadcast.builtin.decoraters import Depend, Middleware
from graia.broadcast.interfaces.decorater import DecoraterInterface
from graia.broadcast.exceptions import PropagationCancelled
import random
from typing import Optional
from devtools import debug
import asyncio
import time
class D1(BaseDispatcher):
    @staticmethod
    def catch(interface: DispatcherInterface):
        if interface.annotation == "123":
            return random.random()

class D2(BaseDispatcher):
    mixin = [D1]
    @staticmethod
    async def catch(interface: DispatcherInterface):
        if interface.annotation == "13":
            r = await interface.execute_with(interface.name, "123", interface.default)
            return r

class TestEvent(BaseEvent):
    class Dispatcher(BaseDispatcher):
        mixin = [D2]

        @staticmethod
        def catch(interface: DispatcherInterface):
            if interface.name == "u":
                yield 1
            elif interface.annotation == str:
                yield 12

event = TestEvent()
loop = asyncio.get_event_loop()
broadcast = Broadcast(loop=loop, debug_flag=True)

@broadcast.receiver("TestEvent")
async def test(u):
    pass

#broadcast.postEvent(TestEvent())
#loop.run_forever()

from vprof import runner

task = asyncio.gather(*[
    broadcast.Executor(ExecutorProtocol(
        target=test,
        event=TestEvent()
    )) for _ in range(40000)
])

runner.run(loop.run_until_complete, "p", args=(task,), host="localhost", port=8990)