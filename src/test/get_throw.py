import asyncio

import pytest
from graia.broadcast import Broadcast
from graia.broadcast.builtin.event import EventExceptionThrown
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
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
async def test_get_exc():
    bcc = Broadcast()
    executed = []

    @bcc.receiver(TestEvent)
    async def _():
        executed.append(1)
        raise Exception("test")

    @bcc.receiver(EventExceptionThrown, dispatchers=[TestDispatcher])
    async def _(ev: EventExceptionThrown, event, exc: Exception, p):
        executed.append(1)
        assert ev.event.__class__ == event.__class__ == TestEvent
        assert ev.exception.__class__ == exc.__class__ == Exception
        assert ev.exception.args == ("test",)
        assert p == 1
        executed.append(1)

    await bcc.postEvent(TestEvent())

    assert len(executed) == 3
