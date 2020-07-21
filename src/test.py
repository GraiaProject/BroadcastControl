from graia.broadcast.entities.event import BaseEvent
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.protocols.executor import ExecutorProtocol
from graia.broadcast.entities.listener import Listener
from graia.broadcast import Broadcast
from graia.broadcast.entities.decorater import Decorater
from graia.broadcast.builtin.decoraters import Depend, Middleware
from graia.broadcast.interfaces.decorater import DecoraterInterface
from graia.broadcast.exceptions import PropagationCancelled
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
            r = await interface.execute_with(interface.name, "123", interface.default)
            return r

class TestEvent(BaseEvent):
    class Dispatcher(BaseDispatcher):
        mixin = [D2]

        @staticmethod
        def catch(interface: DispatcherInterface):
            if interface.name == "u":
                yield 1
            elif interface.annotation == 13:
                yield 12

event = TestEvent()
loop = asyncio.get_event_loop()
broadcast = Broadcast(loop=loop)
m = open("./pylint.conf")
def de1(cc: 13, r_de1 = Middleware(m)):
    assert r_de1.closed == False # 在这里, r.closed 不应该是 True
    print(f"in de1, r.closed is {r_de1.closed}")
    yield cc, 23, r_de1

@broadcast.receiver("TestEvent")
def test(u, r: 13, dii: DispatcherInterface, i: "123" = Depend(de1)):
    print("test", i)
    assert i[2].closed == True
    print("in test, r.closed is", i[2].closed)

@broadcast.receiver("TestEvent", priority=0)
def r():
    raise PropagationCancelled

debug(broadcast.listeners)

async def main():
    broadcast.postEvent(TestEvent())
    await asyncio.sleep(2)
    print(m.closed)

loop.run_until_complete(main())