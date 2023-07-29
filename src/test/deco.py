import asyncio
from typing import Optional

import pytest

from graia.broadcast import Broadcast
from graia.broadcast.builtin.decorators import Depend, OptionalParam
from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.entities.signatures import Force
from graia.broadcast.interfaces.decorator import DecoratorInterface
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


class AsInt(Decorator):
    async def target(self, interface: "DecoratorInterface"):
        return int(interface.return_value) + 1


class Integer(Decorator):
    o: int

    pre = True

    def __init__(self) -> None:
        self.o = 0

    async def target(self, interface: "DecoratorInterface"):
        if interface.name == "int_name":
            return int.__name__
        if interface.annotation is type:
            return int
        if interface.event.__class__ == TestEvent and interface.name == "te":
            return -1
        self.o += 1
        return self.o


class IntWhenInt(Decorator):
    pre = True

    async def target(self, interface: "DecoratorInterface"):
        if interface.annotation is int:
            return 1


@pytest.mark.asyncio
async def test_optional_param():
    bcc = Broadcast()

    executed = []

    @bcc.receiver(TestEvent)
    async def _(
        string: Optional[str] = OptionalParam(IntWhenInt()),
        val: Optional[int] = OptionalParam(IntWhenInt()),
        integer: int = OptionalParam(IntWhenInt()),
    ):
        assert string is None
        assert val is 1
        assert integer is 1
        executed.append(1)

    @bcc.receiver(TestEvent)
    async def _(
        val: Optional[int] = OptionalParam(AsInt()),
    ):
        assert val is None
        executed.append(1)

    await bcc.postEvent(TestEvent())

    assert len(executed) == 2


def test_force_recurse():
    assert Force(Force(Force(None))).target == Force(None).target == Force().target == None


@pytest.mark.asyncio
async def test_decorator():
    bcc = Broadcast()
    deco = AsInt()
    executed = []

    @bcc.receiver(TestEvent)
    async def _(ster=deco):
        assert ster == 2
        executed.append(1)

    await bcc.postEvent(TestEvent())

    assert executed


@pytest.mark.asyncio
async def test_decorator_pre():
    bcc = Broadcast()

    executed = []

    deco = Integer()

    @bcc.receiver(TestEvent)
    async def _(ster=deco, te=deco, int_name=deco, typ: type = deco):
        assert te == -1
        assert int_name == int.__name__
        assert typ == int
        assert ster == deco.o
        executed.append(1)

    for _ in range(5):
        await bcc.postEvent(TestEvent())

    assert len(executed) == 5


async def dep(ster: str, p: int):
    return f"{ster}+{p}"


@pytest.mark.asyncio
async def test_depend():
    bcc = Broadcast()

    executed = []

    @bcc.receiver(TestEvent, dispatchers=[TestDispatcher])
    async def _(ster=Depend(dep)):
        assert ster == "1+1"
        executed.append(1)

    depend = Depend(dep, cache=True)

    @bcc.receiver(TestEvent, dispatchers=[TestDispatcher])
    async def _(a=depend, b=depend):
        assert a == b == "1+1"
        executed.append(1)

    for _ in range(5):
        await bcc.postEvent(TestEvent())

    assert len(executed) == 10
