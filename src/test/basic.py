import asyncio

import pytest

from graia.broadcast import Broadcast
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.entities.signatures import Force
from graia.broadcast.interfaces.dispatcher import DispatcherInterface


class TestDispatcher(BaseDispatcher):
    @staticmethod
    async def catch(interface: DispatcherInterface):
        if interface.name == "p":
            return 1


class TestEvent(Dispatchable):
    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: "DispatcherInterface"):
            if interface.name == "ster":
                return "1"


@pytest.mark.asyncio
async def test_dispatch():
    bcc = Broadcast(
        loop=asyncio.get_running_loop(),
    )

    executed = [False] * 2

    @bcc.receiver(TestEvent)
    async def _1(ster, b: Broadcast, i: DispatcherInterface):
        assert ster == "1"
        assert b is bcc
        assert i.__class__ == DispatcherInterface
        executed[0] = True

    @bcc.receiver(TestEvent, dispatchers=[TestDispatcher])
    async def _2(ster, p):
        assert ster == "1"
        assert p == 1
        executed[1] = True

    await bcc.postEvent(TestEvent())

    assert all(executed)
