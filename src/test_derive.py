import asyncio
from typing import Annotated

from graia.broadcast import Broadcast, Dispatchable
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface


class ExampleEvent(Dispatchable):
    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: "DispatcherInterface"):
            if interface.annotation is str:
                return "ok, i'm."


loop = asyncio.get_event_loop()
broadcast = Broadcast()


async def test_derive_1(v: str, dii: DispatcherInterface):
    print("in derive 1", v)
    return v[1:]


@broadcast.receiver("ExampleEvent")  # or just receiver(ExampleEvent)
async def event_listener(maybe_you_are_str: Annotated[str, test_derive_1, test_derive_1]):
    print(maybe_you_are_str)  # <<< ok, i'm


async def main():
    await broadcast.postEvent(ExampleEvent())  # sync call is allowed.


loop.run_until_complete(main())
