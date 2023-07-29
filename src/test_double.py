import asyncio

# import objgraph
# import copy
import functools
import random
import sys
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


class TestDispatcher(BaseDispatcher):
    @staticmethod
    async def catch(interface: DispatcherInterface):
        if interface.name == "ster":
            return 1


class TestEvent1(Dispatchable):
    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: "DispatcherInterface"):
            if interface.name == "ster":
                return "1"
            elif interface.name == "ster1":
                return 54352345


class TestEvent2(Dispatchable):
    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: "DispatcherInterface"):
            if interface.name == "ster":
                return 6546


event = TestEvent1()
loop = asyncio.new_event_loop()

broadcast = Broadcast()


@broadcast.receiver(TestEvent1)
async def s(e: TestEvent1):
    broadcast.postEvent(TestEvent2(), e)


@broadcast.receiver(TestEvent2)
async def t(e: TestEvent2, ster, ster1):
    print(e, ster, ster1)


loop.run_until_complete(asyncio.wait([broadcast.postEvent(event)]))
