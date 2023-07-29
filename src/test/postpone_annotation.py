from __future__ import annotations

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
async def test_event_dispatch():
    bcc = Broadcast()

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
