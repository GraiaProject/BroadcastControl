import asyncio

# import objgraph
# import copy
import functools
import random
import sys
import time
from typing import Any, Generator, Tuple, Union

import pytest

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
                return "res_ster_1"


class TestEvent2(Dispatchable):
    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: "DispatcherInterface"):
            if interface.name == "ster":
                return "res_ster"


@pytest.mark.asyncio
async def test_():
    event = TestEvent1()

    broadcast = Broadcast(
        loop=asyncio.get_running_loop(),
        debug_flag=False,
    )

    finish = []

    @broadcast.receiver(TestEvent1)
    async def s(e: TestEvent1, ster, ster1):
        assert ster == "1"
        assert ster1 == "res_ster_1"
        broadcast.postEvent(TestEvent2(), e)

    @broadcast.receiver(TestEvent2)
    async def t(e: TestEvent2, ster, ster1):
        assert isinstance(e, TestEvent2)
        assert ster == "res_ster"
        assert ster1 == "res_ster_1"
        finish.append(1)

    await broadcast.postEvent(event)

    assert finish
