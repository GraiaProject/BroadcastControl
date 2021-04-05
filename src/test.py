import traceback
import inspect

original = traceback.print_exc


def modifyed(*args, **kwargs):
    print(inspect.stack()[1])
    return original(*args, **kwargs)


traceback.print_exc = modifyed

from typing import Any, Generator, Literal, Tuple, Union
from graia.broadcast.builtin.factory import (
    AsyncDispatcherContextManager,
    DispatcherContextManager,
    ExcInfo,
    ResponseCodeEnum,
    StatusCodeEnum,
)
from graia.broadcast.entities.event import BaseEvent
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


async def test():
    interface: DispatcherInterface = (yield)
    current_status: StatusCodeEnum = StatusCodeEnum.DISPATCHING  # init stat
    yield
    while current_status is StatusCodeEnum.DISPATCHING:
        result = None

        if interface.annotation.__class__ is int:
            result = interface.annotation + 1

        current_status, external = yield (ResponseCodeEnum.VALUE, result)
    else:
        current_status, external = yield
        if current_status is StatusCodeEnum.DISPATCH_EXCEPTION:
            pass
        current_status, external = yield
        if current_status is StatusCodeEnum.EXECUTION_EXCEPTION:
            pass


class TestEvent(BaseEvent):
    class Dispatcher(BaseDispatcher):
        # mixin = [DispatcherContextManager(test)]

        @staticmethod
        async def catch(interface: "DispatcherInterface"):
            pass


event = TestEvent()
loop = asyncio.get_event_loop()

broadcast = Broadcast(
    loop=loop,
    debug_flag=False,
)


@broadcast.receiver(TestEvent, dispatchers=[AsyncDispatcherContextManager(test)])
async def r(a: 1, b: 2, c: 3):
    # print(a)
    # raise Exception
    pass


count = 20000
use_reference_optimization = True

event = TestEvent()
listener = broadcast.getListener(r)
tasks = []
for _ in range(count):
    # broadcast.postEvent(event)
    tasks.append(broadcast.Executor(listener, event))
s = time.time()

try:
    loop.run_until_complete(asyncio.gather(*tasks))
except:
    pass
# loop.run_until_complete(asyncio.sleep(0.1))
e = time.time()
n = e - s
print(f"used {n}, {count/n}o/s")
print(cached_isinstance.cache_info())
print(cached_getattr.cache_info())
print(listener.param_paths)
