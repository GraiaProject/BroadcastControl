import asyncio

class Broadcast:
    loop: asyncio.AbstractEventLoop
    event_queue: asyncio.Queue

    def __init__(self, loop: asyncio.AbstractEventLoop = None, queue: asyncio.Queue = None):
        self.loop = loop or asyncio.get_event_loop()
        self.event_queue = queue or asyncio.Queue(15)