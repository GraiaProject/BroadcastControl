import asyncio
from typing import Annotated

import pytest

from graia.broadcast import Broadcast, Dispatchable
from graia.broadcast.builtin.derive import Origin
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface


class ExampleEvent(Dispatchable):
    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: "DispatcherInterface"):
            if interface.annotation is str:
                return "ok, i'm."


@pytest.mark.asyncio
async def test_derive():
    broadcast = Broadcast(loop=asyncio.get_event_loop())

    l = []

    async def derive_fun(v: str, dii: DispatcherInterface):
        assert dii.name == "string"
        assert dii.is_annotated
        assert dii.annotated_origin == str
        assert dii.annotated_metadata[-2:] == (derive_fun, derive_fun)
        return v[1:]

    @broadcast.receiver("ExampleEvent")  # or just receiver(ExampleEvent)
    async def _(string: Annotated[str, derive_fun, derive_fun]):
        l.append(string == ", i'm.")

    @broadcast.receiver("ExampleEvent")  # or just receiver(ExampleEvent)
    async def _(string: Annotated[str, Origin(str), derive_fun, derive_fun]):
        l.append(string == ", i'm.")

    await broadcast.postEvent(ExampleEvent())  # sync call is allowed.
    assert l == [True, True]
