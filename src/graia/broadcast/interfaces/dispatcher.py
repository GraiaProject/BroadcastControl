from typing import (
  List, Generator, AsyncGenerator, Union
)
from ..entities.dispatcher import BaseDispatcher
from ..entities.event import BaseEvent
from ..exceptions import OutOfMaxGenerater, InvaildDispatcher
from ..utilles import async_enumerate

import inspect

class DispatcherInterface:
  broadcast: Broadcast
  event: BaseEvent
  dispatchers: List[BaseDispatcher]

  alive_generater_dispatcher: List[Union[Generator, AsyncGenerator]] = []

  _index = 0

  name: str = None
  annotation = None
  default = None

  def __init__(self,
    broadcast_instance: Broadcast,
    event_instance: BaseEvent,
    dispatchers: List[BaseDispatcher]
  ):
    self.broadcast = broadcast_instance
    self.event = event_instance
    self.dispatchers = dispatchers

  async def __aenter__(self):
    return self

  async def __aexit__(self, exc_type, exc, tb):
    await self.alive_dispatcher_killer()
    if tb is not None:
      raise exc

  async def execute_with(self, name: str, annotation, default):
    # here, dispatcher.mixins has been handled.
    self.name, self.annotation, self.default = name, annotation, default
    for self._index, dispatcher in enumerate(
        self.dispatchers[self._index:], start=self._index):
      
      # just allow Dispatcher or any Callable
      if not isinstance(dispatcher, BaseDispatcher) and not callable(dispatcher):
          raise InvaildDispatcher("dispatcher must base on 'BaseDispatcher' or is a callable: ", dispatcher)
      
      if isinstance(dispatcher, BaseDispatcher):
        local_dispatcher = dispatcher().catch
      elif callable(dispatcher):
        local_dispatcher = dispatcher

      result = None

      if inspect.isasyncgenfunction(local_dispatcher) or\
          inspect.isgeneratorfunction(local_dispatcher):
        if inspect.isasyncgenfunction:
          now_dispatcher_generater = await local_dispatcher.__aiter__()
        self.alive_generater_dispatcher.append(now_dispatcher_generater)
        result = next(now_dispatcher_generater)
      else:
        if inspect.iscoroutinefunction(local_dispatcher):
          result = await local_dispatcher(self)
        else:
          result = local_dispatcher(self)

      if result is not None:
        continue

      try:
        return result
      finally:
        await self.alive_dispatcher_killer()

  async def alive_dispatcher_killer(self):
    for unbound_gen in self.alive_generater_dispatcher:
      if inspect.isgenerator(unbound_gen):
        for index, _ in enumerate(unbound_gen, start=1):
          if index == 15:
            raise OutOfMaxGenerater(
              "a dispatch as a sync generator had to stop: ", unbound_gen
            )
      elif inspect.isasyncgen(unbound_gen):
        async for index, _ in async_enumerate(unbound_gen, start=1):
          if index == 15:
            raise OutOfMaxGenerater(
              "a dispatch as a async generator had to stop: ", unbound_gen
            )

from .. import Broadcast