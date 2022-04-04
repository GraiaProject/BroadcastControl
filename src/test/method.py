import asyncio

import pytest

from graia.broadcast import Broadcast
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.entities.signatures import Force
from graia.broadcast.exceptions import InvalidEventName
from graia.broadcast.interfaces.dispatcher import DispatcherInterface


class TestEvent(Dispatchable):
    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: "DispatcherInterface"):
            if interface.name == "ster":
                return "1"


class ChainEvent(TestEvent):
    ...


class NestedEvent(ChainEvent):
    ...


@pytest.mark.asyncio
async def test_fail_lookup():
    bcc = Broadcast(loop=asyncio.get_running_loop())

    with pytest.raises(InvalidEventName):
        bcc.receiver("ImaginaryEvent")(lambda: ...)
    bcc.receiver("NestedEvent")(lambda: ...)
