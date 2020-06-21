import inspect
from typing import AsyncGenerator, Generator, List, Union

from iterwrapper import IterWrapper

from ..entities.dispatcher import BaseDispatcher
from ..entities.event import BaseEvent
from ..entities.signatures import Force
from ..exceptions import (InvaildDispatcher, OutOfMaxGenerater,
                          RequirementCrashed)
from ..utilles import async_enumerate


class DispatcherInterface:
  broadcast: "Broadcast"
  event: BaseEvent
  dispatchers: List[BaseDispatcher]

  alive_generater_dispatcher: List[Union[Generator, AsyncGenerator]] = []

  _index = 0

  name: str = None
  annotation = None
  default = None # dispatcher 允许任何值, 包括 Decorater, 只不过 Decorater Dispatcher 的优先级是隐式最高, 所以基本上不可能截获到.

  def __init__(self,
    broadcast_instance: "Broadcast",
    event_instance: BaseEvent,
    dispatchers: List[BaseDispatcher]
  ):
    self.broadcast = broadcast_instance
    self.event = event_instance
    self.dispatchers = dispatchers

  async def __aenter__(self) -> "DispatchInterface":
    return self

  async def __aexit__(self, exc_type, exc, tb):
    await self.alive_dispatcher_killer()
    if tb is not None:
      raise exc

  async def execute_with(self, name: str, annotation, default):
    # here, dispatcher.mixins has been handled.
    initial_value = (None,) * 3 + (0,)

    if any([self.name is not None, self.annotation is not None, self.default is not None, self._index != 0]):
      initial_value = (self.name, self.annotation, self.default, self._index)
    self.name, self.annotation, self.default = name, annotation, default
    try:
      for self._index, dispatcher in enumerate(
          self.dispatchers[self._index:], start=self._index):

        # just allow Dispatcher or any Callable
        if not isinstance(dispatcher, BaseDispatcher) and not callable(dispatcher):
            raise InvaildDispatcher("dispatcher must base on 'BaseDispatcher' or is a callable: ", dispatcher)
          
        local_dispatcher = None

        if inspect.isclass(dispatcher) and issubclass(dispatcher, BaseDispatcher):
          local_dispatcher = dispatcher().catch
        elif callable(dispatcher) and not inspect.isclass(dispatcher):
          local_dispatcher = dispatcher
        elif isinstance(dispatcher, BaseDispatcher):
          local_dispatcher = dispatcher.catch

        result = None

        if inspect.isasyncgenfunction(local_dispatcher) or\
            (inspect.isgeneratorfunction(local_dispatcher) and \
              not inspect.iscoroutinefunction(local_dispatcher)):
          now_dispatcher_generater = None
          if inspect.isasyncgenfunction(local_dispatcher):
            now_dispatcher_generater = local_dispatcher(self).__aiter__()
            try:
              result = await now_dispatcher_generater.__anext__()
            except StopAsyncIteration as e:
              continue
          else:
            now_dispatcher_generater = local_dispatcher(self).__iter__()
            try:
              result = now_dispatcher_generater.__next__()
            except StopIteration as e:
              result = e.value
          self.alive_generater_dispatcher.append(now_dispatcher_generater)
        else:
          if inspect.iscoroutinefunction(local_dispatcher):
            result = await local_dispatcher(self)
          else:
            result = local_dispatcher(self)

        if result is None:
          continue
        
        if result.__class__ is Force:
          result = result.target

        return result
      else:
        raise RequirementCrashed("the dispatching requirement crashed: ", self.name, self.annotation, self.default)
    finally:
        self.name, self.annotation, self.default, self._index = initial_value

  async def alive_dispatcher_killer(self):
    for unbound_gen in self.alive_generater_dispatcher:
      if inspect.isgenerator(unbound_gen):
        for index, _ in enumerate(unbound_gen, start=1):
          if index == 16:
            raise OutOfMaxGenerater(
              "a dispatch as a sync generator had to stop: ", unbound_gen
            )
      elif inspect.isasyncgen(unbound_gen):
        async for index, _ in async_enumerate(unbound_gen, start=1):
          if index == 16:
            raise OutOfMaxGenerater(
              "a dispatch as a async generator had to stop: ", unbound_gen
            )

  @staticmethod
  def dispatcher_mixin_handler(dispatcher: BaseDispatcher) -> List[BaseDispatcher]:
    unbound_mixin = getattr(dispatcher, "mixin", [])
    if not unbound_mixin:
      return [dispatcher]

    return [dispatcher, *(IterWrapper(unbound_mixin)
      .filter(lambda x: issubclass(x, BaseDispatcher))
      .map(lambda x: DispatcherInterface.dispatcher_mixin_handler(x))
      .flat().collect(list)
    )]
