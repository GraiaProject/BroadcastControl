import asyncio

from graia.broadcast import Broadcast, Dispatchable
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface


class ExampleEvent(Dispatchable):
    class Dispatcher(BaseDispatcher):
        @staticmethod
        def catch(interface: "DispatcherInterface"):
            if interface.annotation is str:
                return "ok, i'm."


loop = asyncio.get_event_loop()
broadcast = Broadcast()


@broadcast.receiver("ExampleEvent")  # or just receiver(ExampleEvent)
async def event_listener(maybe_you_are_str: str):
    print(maybe_you_are_str)  # <<< ok, i'm


async def main():
    broadcast.postEvent(ExampleEvent())  # sync call is allowed.


loop.run_until_complete(main())
