import asyncio

from graia.broadcast import Broadcast
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.interfaces.dispatcher import DispatcherInterface


class TestDispatcher(BaseDispatcher):
    @classmethod
    async def beforeExecution(cls, interface: DispatcherInterface):
        if interface.depth == 0:
            print("beforeExecution")

    @classmethod
    async def catch(cls, interface: DispatcherInterface):
        if interface.name == "ster":
            return 1


class TestEvent(Dispatchable):
    class Dispatcher(BaseDispatcher):
        mixin = [TestDispatcher]

        @classmethod
        async def catch(cls, interface: "DispatcherInterface"):
            if interface.name == "ster1":
                return "1"
            elif interface.name == "ster2":
                return 54352345

        @classmethod
        async def afterExecution(
            self,
            interface: DispatcherInterface,
            *args,
        ):
            if interface.depth == 0:
                print("afterExecution")


event = TestEvent()
loop = asyncio.new_event_loop()

broadcast = Broadcast(
    loop=loop,
    debug_flag=False,
)


@broadcast.receiver(
    TestEvent,
    decorators=[
        Depend(lambda ster: print("depend: ster", ster)),
        Depend(lambda ster1: print("depend: ster1", ster1)),
        Depend(lambda ster2: print("depend: ster2", ster2)),
    ],
)
async def s(e: TestEvent):
    print(e)


def error(ster: int):
    raise ValueError("error", ster)


@broadcast.receiver(TestEvent, decorators=[Depend(error)])
async def s1(e: TestEvent):
    print(e)


loop.run_until_complete(asyncio.wait([broadcast.postEvent(event)]))
