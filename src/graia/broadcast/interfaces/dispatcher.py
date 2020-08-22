from typing import Any, AsyncGenerator, Callable, Generator, List, Optional, Tuple, Type, Union, _GenericAlias

from ..entities.dispatcher import BaseDispatcher
from ..entities.event import BaseEvent
from ..entities.signatures import Force
from ..exceptions import (OutOfMaxGenerater,
                          RequirementCrashed)
from ..utilles import is_asyncgener, isgeneratorfunction, run_always_await

def get_raw_dispatcher_callable(dispatcher: Any):
  if isinstance(dispatcher, BaseDispatcher):
    return dispatcher.catch
  if callable(dispatcher):
    return dispatcher

class ContextStackItem:
  __slots__ = ("dispatchers", "event")

  dispatchers: List[BaseDispatcher]
  event: BaseEvent

  def __init__(self, dispatchers: List[BaseDispatcher], event: BaseEvent) -> None:
    self.dispatchers = dispatchers
    self.event = event

class ExecuteContextStackItem:
  def __init__(self, name, annotation, default, local_dispatchers, optional=False, index=0) -> None:
    self.name, self.annotation, self.default, self.local_dispatchers, self.index = \
      name, annotation, default, local_dispatchers, index
    self.optional = optional
    self.always_dispatchers = []
    for i in local_dispatchers:
      if isinstance(i, BaseDispatcher) and i.always:
        self.always_dispatchers.append(i)
  
  def __repr__(self) -> str:
    return "<ContextStackItem name={0} annotation={1} default={2} locald={3} index={4}>"\
      .format(
        self.name, self.annotation, self.default, self.local_dispatchers, self.index)

  name: str
  annotation: Any
  default: Any
  local_dispatchers: List[Union[BaseDispatcher, Callable]]
  optional: bool
  index: int

  # 即 无论如何都会被激活至少 1 次的 Dispatchers.
  always_dispatchers: List[Union[BaseDispatcher, Callable]]

  __slots__ = ("name", "annotation", "default", "local_dispatchers", "optional", "index", "always_dispatchers")

class DispatcherInterface:
  __slots__ = ("broadcast", "execute_context_stack", "context_stack", "alive_generater_dispatcher")

  broadcast: "Broadcast"

  execute_context_stack: List[ExecuteContextStackItem]
  context_stack: List[ContextStackItem]
  alive_generater_dispatcher: List[
    List[Tuple[Union[Generator, AsyncGenerator], bool]]
    # True => async, False => sync
  ]

  @property
  def name(self):
    return self.execute_context_stack[-1].name

  @property
  def annotation(self):
    return self.execute_context_stack[-1].annotation

  @property
  def default(self):
    return self.execute_context_stack[-1].default

  @property
  def _index(self):
    return self.execute_context_stack[-1].index

  @_index.setter
  def _(self, new_value):
    self.execute_context_stack[-1].index = new_value

  @property
  def local_dispatchers(self):
    return self.execute_context_stack[-1].local_dispatchers

  @property
  def dispatchers(self):
    return self.context_stack[-1].dispatchers
  
  @property
  def event(self):
    return self.context_stack[-1].event

  # dispatcher 允许任何值, 包括 Decorater, 只不过 Decorater Dispatcher 的优先级是隐式最高, 所以基本上不可能截获到.

  def __init__(self, broadcast_instance: "Broadcast"):
    self.broadcast = broadcast_instance
    self.alive_generater_dispatcher = [[]]
    self.context_stack = []
    self.execute_context_stack =\
      [ExecuteContextStackItem(None, None, None, [], 0)]
  
  def enter_context(self, event: BaseEvent, dispatchers: List[BaseDispatcher]):
    self.context_stack.append(ContextStackItem(dispatchers, event))
    for i in self.dispatchers[self._index:]:
      if getattr(i, "always", False):
        self.always_dispatcher.append(i)
    return self

  async def __aenter__(self) -> "DispatcherInterface":
    return self

  async def __aexit__(self, _, exc, tb):
    if len(self.alive_generater_dispatcher) != 0:
      await self.alive_dispatcher_killer()
      self.alive_generater_dispatcher.pop()
    self.context_stack.pop()

    if tb is not None:
      raise exc

  def inject_local_dispatcher(self, *dispatchers: List[Union[BaseDispatcher, Callable]]):
    self.local_dispatchers.extend(dispatchers)
    always_dispatchers = self.execute_context_stack[-1].always_dispatchers

    for i in dispatchers:
      if getattr(i, "always", False):
        always_dispatchers.append(i)

  def inject_global_dispatcher(self, *dispatchers: List[Union[BaseDispatcher, Callable]]):
    self.dispatchers.extend(dispatchers)
    always_dispatchers = self.execute_context_stack[-1].always_dispatchers

    for i in dispatchers:
      if getattr(i, "always", False):
        always_dispatchers.append(i)

  async def execute_with(self, name: str, annotation, default):
    optional = False
    if isinstance(annotation, _GenericAlias):
      if annotation.__origin__ is Union and annotation.__args__[-1] is type(None):
        # 如果是 Optional, 则它的最后一位应为 NoneType.
        optional = True
        annotation = annotation.__args__[0]
      else:
        raise TypeError("cannot parse this annotation: {0}".format(annotation))

    self.execute_context_stack.append(ExecuteContextStackItem(name, annotation, default, [], optional=optional))

    alive_dispatchers = []
    self.alive_generater_dispatcher.append(alive_dispatchers)
    
    always_dispatcher = self.execute_context_stack[-1].always_dispatchers
    
    result = None
    try:
      for self.execute_context_stack[-1].index, dispatcher in enumerate(
          self.dispatchers[self._index:], start=self._index):
        
        if getattr(dispatcher, "always", False):
          try: always_dispatcher.remove(dispatcher)
          except: pass

        if isinstance(dispatcher, type) and issubclass(dispatcher, BaseDispatcher):
          local_dispatcher = dispatcher().catch
        elif isinstance(dispatcher, BaseDispatcher):
          local_dispatcher = dispatcher.catch
        elif callable(dispatcher):
          local_dispatcher = dispatcher
        else:
          raise ValueError("invaild dispatcher: ", dispatcher)

        if is_asyncgener(local_dispatcher):
          now_dispatcher_generater = local_dispatcher(self).__aiter__()

          try:
            result = await now_dispatcher_generater.__anext__()
          except StopAsyncIteration:
            continue
          else:
            alive_dispatchers.append(
              (now_dispatcher_generater, True)
            )
        elif isgeneratorfunction(local_dispatcher):
          now_dispatcher_generater = local_dispatcher(self).__iter__()

          try:
            result = now_dispatcher_generater.__next__()
          except StopIteration as e:
            result = e.value
          else:
            alive_dispatchers.append(
              (now_dispatcher_generater, False)
            )
        else:
          result = await run_always_await(local_dispatcher(self))

        if result is None:
          continue
        
        if result.__class__ is Force:
          result = result.target

        return result
      else:
        if optional:
          return None
        raise RequirementCrashed("the dispatching requirement crashed: ", self.name, self.annotation, self.default)
    finally: # 在某种程度上, 这算 BCC 内的第二个 "无头充数" 的设计了.
      for always_dispatcher in always_dispatcher:
        if isinstance(always_dispatcher, type) and issubclass(always_dispatcher, BaseDispatcher):
          local_dispatcher = always_dispatcher().catch
        elif isinstance(always_dispatcher, BaseDispatcher):
          local_dispatcher = always_dispatcher.catch
        elif callable(always_dispatcher):
          local_dispatcher = always_dispatcher
        else:
          raise ValueError("invaild dispatcher: ", always_dispatcher)

        if is_asyncgener(local_dispatcher):
          now_dispatcher_generater = local_dispatcher(self).__aiter__()
          alive_dispatchers.append(
            (now_dispatcher_generater, True)
          )

          try:
            await now_dispatcher_generater.__anext__()
          except StopAsyncIteration:
            pass
        elif isgeneratorfunction(local_dispatcher):
          now_dispatcher_generater = local_dispatcher(self).__iter__()
          alive_dispatchers.append(
            (now_dispatcher_generater, False)
          )

          try:
            now_dispatcher_generater.__next__()
          except StopIteration as e:
            pass
        else:
          await run_always_await(local_dispatcher(self))

      self.execute_context_stack.pop()

  async def alive_dispatcher_killer(self):
    for unbound_gen, is_async_gen in self.alive_generater_dispatcher[-1]:
      index = 0
      if is_async_gen:
        async for _ in unbound_gen:
          if index == 15:
            raise OutOfMaxGenerater(
              "a dispatch as a sync generator had to stop: ", unbound_gen
            )
          index += 1
      else:
        for _ in unbound_gen:
          if index == 15:
            raise OutOfMaxGenerater(
              "a dispatch as a sync generator had to stop: ", unbound_gen
            )
          index += 1
  
  def getDispatcher(self, dispatcher_class: Type[BaseDispatcher]) -> Optional[BaseDispatcher]:
    for i in self.dispatchers:
      if type(i) is dispatcher_class:
        return i