from graia.broadcast.entities.event import BaseEvent
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.protocols.executor import ExecutorProtocol
from graia.broadcast.entities.listener import Listener
from graia.broadcast import Broadcast
import random
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

async def main():
    def test(u, r: 13, i: "123"):
        print(u, r, i)
    loop = asyncio.get_running_loop()
    loop.create_task(broadcast.event_runner())
    for _ in range(2):
        broadcast.listeners.append(Listener(
            callable=test,
            namespace=broadcast.default_namespace,
            listening_events=[
                TestEvent
            ]
        ))
    await broadcast.postEvent(TestEvent())
    await asyncio.sleep(10)

loop.run_until_complete(main())