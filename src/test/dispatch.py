import asyncio

import pytest

from graia.broadcast import Broadcast
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.entities.signatures import Force
from graia.broadcast.exceptions import ExecutionStop, RequirementCrashed
from graia.broadcast.interfaces.dispatcher import DispatcherInterface


class RandomDispatcher(BaseDispatcher):
    def __init__(self, t: bool = False) -> None:
        self.second_exec = t

    async def catch(self, interface: DispatcherInterface):
        if interface.name == "p":
            return "P_dispatcher"
        elif interface.name == "f":
            if self.second_exec:
                return
            self.second_exec = True
            return Force(2)


class CrashDispatcher(BaseDispatcher):
    @staticmethod
    async def catch(i: DispatcherInterface):
        i.crash()


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
    bcc = Broadcast()

    dii = DispatcherInterface(bcc, [])

    assert await dii.lookup_by_directly(RandomDispatcher(), "p", None, None) == "P_dispatcher"
    assert await dii.lookup_by_directly(RandomDispatcher(), "f", None, None) == 2


@pytest.mark.asyncio
async def test_crash():
    bcc = Broadcast()

    dii = DispatcherInterface(bcc, [])
    with pytest.raises(RequirementCrashed):
        await dii.lookup_by_directly(CrashDispatcher, "u", None, None)
    with pytest.raises(ExecutionStop):
        dii.stop()


@pytest.mark.asyncio
async def test_insert():
    bcc = Broadcast()

    dii = DispatcherInterface(bcc, [])

    t_a = RandomDispatcher()
    t_b = RandomDispatcher()
    dii.inject_execution_raw(t_a, t_b)
    assert dii.dispatchers == [t_b, t_a]


@pytest.mark.asyncio
async def test_event_dispatch():
    bcc = Broadcast()

    executed = []

    @bcc.receiver(TestEvent)
    async def _1(
        ster,
        p,
        b: Broadcast,
        e: TestEvent,
        e1: Dispatchable,
        i: DispatcherInterface,
        i1: DispatcherInterface[TestEvent],
    ):
        assert ster == "1"
        assert p == "P_event"
        assert b is bcc
        assert e.__class__ is TestEvent
        assert e1.__class__ is TestEvent
        assert i.__class__ is DispatcherInterface
        assert i1.__class__ is DispatcherInterface
        executed.append(1)

    await bcc.postEvent(TestEvent())

    assert len(executed) == 1


@pytest.mark.asyncio
async def test_dispatcher_catch():
    bcc = Broadcast()

    executed = []

    @bcc.receiver(TestEvent, dispatchers=[RandomDispatcher(), RandomDispatcher()])
    async def _1(f, b: Broadcast, i: DispatcherInterface):
        assert f == 2
        assert b is bcc
        assert i.__class__ == DispatcherInterface
        executed.append(1)

    await bcc.postEvent(TestEvent())
    await bcc.postEvent(TestEvent())

    assert len(executed) == 2


@pytest.mark.asyncio
@pytest.mark.xfail  # need further discussion
async def test_dispatcher_priority():
    bcc = Broadcast()

    executed = []

    @bcc.receiver(TestEvent, dispatchers=[RandomDispatcher])
    async def _2(ster, p):
        assert ster == "1"
        assert p == "P_dispatcher"
        executed.append(1)

    await bcc.postEvent(TestEvent())

    assert len(executed) == 1
