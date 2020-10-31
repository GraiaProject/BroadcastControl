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
import objgraph
import copy

#print(objgraph.most_common_types(20))

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
            r = await interface.lookup_param(interface.name, "123", interface.default)
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
#loop.set_debug(True)
broadcast = Broadcast(loop=loop, debug_flag=True)

i = 0
l = asyncio.Lock()

@broadcast.receiver(TestEvent)
async def r(u, v: str, p: "123"):
    global i
    async with l:
        i += 1

async def main():
    #print("将在 5 s 后开始测试.")
    #for i in range(1, 6):
    #    print(i)
    #    await asyncio.sleep(1)
    #print("测试开始.", start)
    #for _ in range(100000):
    #    broadcast.postEvent(TestEvent())
    #end = time.time()
    #print(f"事件广播完毕, 总共 10000 个, 当前时间: {end}, 用时: {end - start - 5}")
    listener = broadcast.getListener(r)
    start = time.time()
    await asyncio.gather(*[broadcast.Executor(
        listener, event,
        #use_dispatcher_statistics=True, use_reference_optimization=True
    ) for _ in range(100000)])
    end = time.time()
    print(end - start)
    debug(listener.dispatcher_statistics)
    print(i)

loop.run_until_complete(main())