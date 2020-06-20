from graia.broadcast.entities.event import BaseEvent
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

class D1(BaseDispatcher):
    @staticmethod
    def catch(interface: DispatcherInterface):
        if interface.annotation == "123":
            return 123

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

async def main():
    print(DispatcherInterface.dispatcher_mixin_handler(TestEvent.Dispatcher))
    async with DispatcherInterface(1, event, 
            DispatcherInterface.dispatcher_mixin_handler(TestEvent.Dispatcher)) as interface:
        interface: DispatcherInterface
        print(await interface.execute_with("u", 1, 1))
        print(await interface.execute_with("r", "13", 1))
        print("start kill")

import asyncio
asyncio.run(main())