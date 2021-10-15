from typing import Any, Generator, Literal, Tuple, Union
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.entities.listener import Listener
from graia.broadcast import Broadcast
from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.interfaces.decorator import DecoratorInterface
from graia.broadcast.exceptions import ExecutionStop, PropagationCancelled
from graia.broadcast.interrupt import InterruptControl
from graia.broadcast.interrupt.waiter import Waiter
import random
import asyncio
import time

# import objgraph
# import copy
import functools

from graia.broadcast.utilles import dispatcher_mixin_handler


class TestEvent(Dispatchable):
    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: "DispatcherInterface"):
            if interface.annotation is str:
                return "1"

        @staticmethod
        async def beforeDispatch(interface: "DispatcherInterface"):
            pass


@Waiter.create_using_function([TestEvent])
def waiter(event: TestEvent):
    return 1


event = TestEvent()
loop = asyncio.get_event_loop()

broadcast = Broadcast(
    loop=loop,
    debug_flag=False,
)


@broadcast.receiver(TestEvent)
async def r(r: str, d: str, c: str):
    # loop.call_later(1, lambda: broadcast.postEvent(TestEvent()))
    # print(await inc.wait(waiter))
    pass


count = 100000

event = TestEvent()
listener = broadcast.getListener(r)
tasks = []
import cProfile

mixins = dispatcher_mixin_handler(event.Dispatcher)
print(mixins)
for _ in range(count):
    # broadcast.postEvent(event)
    # tasks.append(
    #    loop.create_task(broadcast.Executor(listener, event)))
    tasks.append(broadcast.Executor(listener, dispatchers=mixins))

#import yappi

s = time.time()

"""
yappi.set_clock_type("WALL")
with yappi.run():
    loop.run_until_complete(asyncio.gather(*tasks))
yappi.get_func_stats().print_all(
    columns={ 0: ("name", 60),1: ("ncall", 8),2: ("tsub", 10),3: ("ttot", 10),4: ("tavg", 10) }
)
"""
loop.run_until_complete(asyncio.gather(*tasks))


"""
try:
    #cProfile.run("loop.run_until_complete(asyncio.gather(*tasks))", "perf.prof")
    loop.run_until_complete(asyncio.gather(*tasks))
    # loop.run_until_complete(asyncio.gather(*[r(1, 2, 3, 4) for _ in range(count)]))
except:
    pass
"""
# loop.run_until_complete(asyncio.sleep(0.1))
e = time.time()
n = e - s
print(f"used {n}, {count/n}o/s")
# print(tasks)
print(listener.maybe_failure)
print(listener.param_paths)
