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
            elif interface.annotation == 13:
                yield 12

event = TestEvent()
loop = asyncio.get_event_loop()
broadcast = Broadcast(loop=loop)
def de1(cc: 13):
    pass

@broadcast.receiver("TestEvent")
async def test(u, r: 13):
    await asyncio.sleep(4 + random.random())

"""
tasks = [broadcast.layered_scheduler(
    listener_generator=broadcast.default_listener_generator(event.__class__),
    event=event
) for _ in range(10000)]
"""
tasks = [broadcast.Executor(ExecutorProtocol(
    target=test,
    event=event
)) for _ in range(10000)]

import cProfile, pstats, io

pr = cProfile.Profile()
pr.enable()

loop.run_until_complete(asyncio.wait(tasks))

pr.disable()
s = io.StringIO()
sortby = "cumtime"  # 仅适用于 3.6, 3.7 把这里改成常量了
ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
ps.print_stats()
print(s.getvalue())
pr.dump_stats("pipeline.prof")