import asyncio
from .entities.namespace import Namespace
from typing import List, AsyncGenerator, Generator
from .entities.event import BaseEvent
from .interfaces.dispatcher import DispatcherInterface
from .protocols.executor import ExecutorProtocol
from iterwrapper import IterWrapper as iw
from .entities.listener import Listener
from .utilles import iw_group

class Broadcast:
  loop: asyncio.AbstractEventLoop
  event_queue: asyncio.Queue

  default_namespace: Namespace
  namespaces: List[Namespace] = []
  listeners: List[Listener]

  stoped: bool = False

  def __init__(self, loop: asyncio.AbstractEventLoop = None, queue: asyncio.Queue = None):
    self.loop = loop or asyncio.get_event_loop()
    self.event_queue = queue or asyncio.Queue(15)
    self.default_namespace = Namespace(name="default", default=True)

  async def event_generator(self) -> AsyncGenerator[BaseEvent]:
      while True:
        try:
          yield await asyncio.wait_for(self.event_queue.get(), timeout=5)
        except asyncio.TimeoutError:
          continue
        except asyncio.CancelledError:
          return
  
  def listener_generator(self) -> Listener:
    yield from (iw_group(iw(self.listeners)
      .filter(lambda x: not x.namespace.hide) # filter for hide
      .filter(lambda x: not x.namespace.disabled), # filter for disabled
        key=lambda x: x.namespace.name # group
      ).map(lambda x: iw(x).apply(list.sort, key=lambda x: x.priority).collect(list)) # sort in group
      .flat() # unpack
      .collect(list) # collect to a whole list
    )

  async def event_runner(self):
    async for event in self.event_generator():
      for listener in self.listener_generator():
        self.loop.create_task(self.Executor(ExecutorProtocol(
          target=listener,
          event=event,
          dispatchers=DispatcherInterface.dispatcher_mixin_handler(
            event.Dispatcher
          )
        )))
      
  async def Executor(self, protocol: ExecutorProtocol):
    pass