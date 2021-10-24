import asyncio

# import objgraph
# import copy
import functools
import random
import time
from typing import Any, Generator, Tuple, Union

from graia.broadcast import Broadcast
from graia.broadcast.bypass import BypassBroadcast
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.entities.listener import Listener
from graia.broadcast.exceptions import ExecutionStop, PropagationCancelled
from graia.broadcast.interfaces.decorator import DecoratorInterface
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.interrupt import InterruptControl
from graia.broadcast.interrupt.waiter import Waiter
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


class SubEvent(TestEvent):
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
    pass


count = 40000

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


s = time.time()
"""
from pyinstrument import Profiler

profiler = Profiler()
profiler.start()
"""
loop.run_until_complete(asyncio.gather(*tasks))
"""
profiler.stop()

profiler.open_in_browser()
"""

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


broadcast = BypassBroadcast(
    loop=loop,
    debug_flag=False,
)


@broadcast.receiver(TestEvent)
async def r(r: str, d: str, c: str):
    pass


count = 40000

event = SubEvent()
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


s = time.time()

"""
from pyinstrument import Profiler

profiler = Profiler()
profiler.start()
"""
loop.run_until_complete(asyncio.gather(*tasks))
"""
profiler.stop()

profiler.open_in_browser()
"""


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
