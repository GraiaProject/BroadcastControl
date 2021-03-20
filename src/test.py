from typing import Any
from graia.broadcast.entities.event import BaseEvent
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.entities.listener import Listener
from graia.broadcast import Broadcast
from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.interfaces.decorator import DecoratorInterface
from graia.broadcast.exceptions import PropagationCancelled
from graia.broadcast.interrupt import InterruptControl
from graia.broadcast.interrupt.waiter import Waiter
import random
import asyncio
import time
import objgraph
import copy
import functools
from graia.broadcast.utilles import cached_isinstance, cached_getattr

from graia.broadcast.utilles import dispatcher_mixin_handler

# print(objgraph.most_common_types(20))


class D1(BaseDispatcher):
    @staticmethod
    async def catch(interface: "DispatcherInterface"):
        if interface.annotation == "123":
            return random.random()


class D2(BaseDispatcher):
    mixin = [D1]

    @staticmethod
    async def catch(interface: "DispatcherInterface"):
        if interface.annotation == "13":
            r = await interface.lookup_param(interface.name, "123", interface.default)

            return r


class TestEvent(BaseEvent):
    class Dispatcher(BaseDispatcher):
        mixin = [D2]

        @staticmethod
        async def catch(interface: "DispatcherInterface"):
            if interface.name == "u":
                return 1
            elif interface.annotation == str:
                return 12


event = TestEvent()
loop = asyncio.get_event_loop()

broadcast = Broadcast(
    loop=loop,
    debug_flag=False,
)


@broadcast.receiver(TestEvent)
async def r(a: "123", b: "123", c: "123"):
    # async def r():
    # print(locals())
    # print(1)
    pass


import vprof.runner

count = 20000
enable_vprof = False
use_reference_optimization = True

event = TestEvent()
listener = broadcast.getListener(r)
tasks = []
for _ in range(count):
    # broadcast.postEvent(event)
    tasks.append(broadcast.Executor(listener, event))
s = time.time()

if enable_vprof:
    vprof.runner.run(
        loop.run_until_complete,
        "p",
        (asyncio.gather(*tasks),),
    )
else:
    loop.run_until_complete(asyncio.gather(*tasks))
# loop.run_until_complete(asyncio.sleep(0.1))
e = time.time()
n = e - s
print(f"used {n}, {count/n}o/s")
print(cached_isinstance.cache_info())
print(cached_getattr.cache_info())
print(listener.param_paths)
