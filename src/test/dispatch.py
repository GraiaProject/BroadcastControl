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
            return "P_dispatcher"
        elif interface.name == "f":
            return Force(2)


class TestEvent(Dispatchable):
    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: "DispatcherInterface"):
            if interface.name == "ster":
                return "1"
            if interface.name == "p":
                return "P_event"


@pytest.mark.asyncio
async def test_lookup_directly():
    bcc = Broadcast(
        loop=asyncio.get_running_loop(),
    )

    dii = DispatcherInterface(bcc, [])

    assert await dii.lookup_by_directly(TestDispatcher, "p", None, None) == "P_dispatcher"
    assert await dii.lookup_by_directly(TestDispatcher, "f", None, None) == 2


@pytest.mark.asyncio
async def test_insert():
    bcc = Broadcast(
        loop=asyncio.get_running_loop(),
    )

    dii = DispatcherInterface(bcc, [])

    t_a = TestDispatcher()
    t_b = TestDispatcher()
    dii.inject_execution_raw(t_a, t_b)
    assert dii.dispatchers == [t_b, t_a]


@pytest.mark.asyncio
async def test_event_dispatch():
    bcc = Broadcast(
        loop=asyncio.get_running_loop(),
    )

    executed = []

    @bcc.receiver(TestEvent)
    async def _1(ster, p, b: Broadcast, i: DispatcherInterface):
        assert ster == "1"
        assert p == "P_event"
        assert b is bcc
        assert i.__class__ == DispatcherInterface
        executed.append(1)

    await bcc.postEvent(TestEvent())

    assert len(executed) == 1


@pytest.mark.asyncio
async def test_dispatcher_catch():
    bcc = Broadcast(
        loop=asyncio.get_running_loop(),
    )

    executed = []

    @bcc.receiver(TestEvent, dispatchers=[TestDispatcher])
    async def _1(f, b: Broadcast, i: DispatcherInterface):
        assert f == 2
        assert b is bcc
        assert i.__class__ == DispatcherInterface
        executed.append(1)

    await bcc.postEvent(TestEvent())

    assert len(executed) == 1


@pytest.mark.asyncio
@pytest.mark.xfail  # need further discussion
async def test_dispatcher_priority():
    bcc = Broadcast(
        loop=asyncio.get_running_loop(),
    )

    executed = []

    @bcc.receiver(TestEvent, dispatchers=[TestDispatcher])
    async def _2(ster, p):
        assert ster == "1"
        assert p == "P_dispatcher"
        executed.append(1)

    await bcc.postEvent(TestEvent())

    assert len(executed) == 1
