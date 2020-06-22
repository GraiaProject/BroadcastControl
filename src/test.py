from graia.broadcast.entities.event import BaseEvent
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.protocols.executor import ExecutorProtocol
from graia.broadcast.entities.listener import Listener
from graia.broadcast import Broadcast
from graia.broadcast.entities.decorater import Decorater
from graia.broadcast.builtin.decoraters import Depend, Middleware
from graia.broadcast.interfaces.decorater import DecoraterInterface
import random
from devtools import debug
import asyncio

class D1(BaseDispatcher):
    @staticmethod
    def catch(interface: DispatcherInterface):
        if interface.annotation == "123":
            return random.random()

class D2(BaseDispatcher):
    mixin = [D1]
    @staticmethod
    async def catch(interface: DispatcherInterface):
        if interface.annotation == "13":
            print(list(map(lambda x: getattr(interface, x), ['name', 'annotation', "default", "_index"])))
            r = await interface.execute_with(interface.name, "123", interface.default)
            print(list(map(lambda x: getattr(interface, x), ['name', 'annotation', "default", "_index"])))
            return r

class TestEvent(BaseEvent):
    class Dispatcher(BaseDispatcher):
        mixin = [
            D2
        ]

        @staticmethod
        def catch(interface: DispatcherInterface):
            if interface.name == "u":
                yield 1
            elif interface.annotation == 13:
                yield 12

event = TestEvent()
loop = asyncio.get_event_loop()
broadcast = Broadcast(loop=loop)
def de1(cc: 13):
    yield cc, 23

m = open("./pylint.conf")

@broadcast.receiver("TestEvent")
def test(u, r: 13, i: "123" = Depend(de1), oc=Middleware(m)):
    print(u, r, i, debug(oc), oc.closed)

async def main():
    loop = asyncio.get_running_loop()
    loop.create_task(broadcast.event_runner())
    await broadcast.postEvent(TestEvent())
    await asyncio.sleep(10)
    print(m.closed)

loop.run_until_complete(main())