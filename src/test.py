import asyncio

# import objgraph
# import copy
import functools
import random
import time
from typing import Any, Generator, Tuple, Union

from graia.broadcast import Broadcast
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.entities.exectarget import ExecTarget
from graia.broadcast.entities.listener import Listener
from graia.broadcast.exceptions import ExecutionStop, PropagationCancelled
from graia.broadcast.interfaces.decorator import DecoratorInterface
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.interrupt import InterruptControl
from graia.broadcast.interrupt.waiter import Waiter
from graia.broadcast.utilles import dispatcher_mixin_handler

import sys


class TestDispatcher(BaseDispatcher):
    @staticmethod
    async def catch(interface: DispatcherInterface):
        if interface.name == "ster":
            return 1


class TestEvent(Dispatchable):
    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: "DispatcherInterface"):
            if interface.name == "ster":
                return "1"


class AsInt(Decorator):
    o: int = 0

    async def target(self, interface: "DecoratorInterface"):
        self.o += 1
        return int(interface.return_value)


event = TestEvent()
loop = asyncio.get_event_loop()

broadcast = Broadcast(
    loop=loop,
    debug_flag=False,
)

p = AsInt()


@broadcast.receiver(TestEvent)
async def r(ster):
    pass


count = 100000

event = TestEvent()
listener = broadcast.getListener(r)
tasks = []
import cProfile

mixins = dispatcher_mixin_handler(event.Dispatcher)
for _ in range(count):
    # broadcast.postEvent(event)
    # tasks.append(
    #    loop.create_task(broadcast.Executor(listener, event)))
    tasks.append(broadcast.Executor(listener, dispatchers=mixins.copy()))

s = time.time()
# print(s)
# cProfile.run("loop.run_until_complete(asyncio.gather(*tasks))")
loop.run_until_complete(asyncio.gather(*tasks))

e = time.time()
n1 = e - s

s2 = time.time()
# loop.run_until_complete(asyncio.gather(*[r(1) for _ in range(count)]))
e2 = time.time()
n2 = e2 - s2


# loop.run_until_complete(asyncio.sleep(0.1))
print(n1, count, n2)
print(f"used {n1}, {count/n1}o/s,")
print(listener.oplog)
print(p.o)
# print(tasks)
