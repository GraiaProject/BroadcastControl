import itertools
from typing import (Any, AsyncGenerator, Callable, Generator, List, Optional,
                    Set, Tuple, Type, Union, _GenericAlias)

from ..entities.dispatcher import BaseDispatcher
from ..entities.event import BaseEvent
from ..entities.signatures import Force
from ..exceptions import OutOfMaxGenerater, RequirementCrashed
from ..utilles import (as_sliceable, is_asyncgener, isgeneratorfunction,
                       run_always_await_safely)


def get_raw_dispatcher_callable(dispatcher: Any):
  if isinstance(dispatcher, BaseDispatcher):
    return dispatcher.catch
  if callable(dispatcher):
    return dispatcher

class EmptyEvent(BaseEvent):
  class Dispatcher:
    @staticmethod
    def catch(_):
      pass

class ExecutionContext:
  __slots__ = ("dispatchers", "always_dispatchers", "event", "inline_generator", "_index")

  dispatchers: List[BaseDispatcher]
  always_dispatchers: Set[Union[BaseDispatcher, Callable]]
  event: BaseEvent
  inline_generator: bool
  _index: int

  def __init__(self, dispatchers: List[BaseDispatcher], event: BaseEvent, inline_generator: bool = False) -> None:
    self.dispatchers = dispatchers
    self.event = event
    self.inline_generator = inline_generator
    self._index = 0
  
    self.always_dispatchers = set()
    for i in dispatchers:
      if isinstance(i, BaseDispatcher) and i.always:
        self.always_dispatchers.add(i)

class ParameterContext:
  def __init__(self, name, annotation, default, dispatchers, optional=False) -> None:
    self.name, self.annotation, self.default, self.dispatchers = \
      name, annotation, default, dispatchers
    self.optional = optional
  
  def __repr__(self) -> str:
    return "<ParameterContext name={0} annotation={1} default={2} locald={3}"\
      .format(
        self.name, self.annotation, self.default, self.dispatchers)

  name: str
  annotation: Any
  default: Any
  dispatchers: List[Union[BaseDispatcher, Callable]]
  optional: bool

  __slots__ = ("name", "annotation", "default", "dispatchers", "optional")

class DispatcherInterface:
  __slots__ = ("broadcast", "execution_contexts", "parameter_contexts", "alive_generater_dispatcher")

  broadcast: "Broadcast"

  execution_contexts: List[ExecutionContext]
  parameter_contexts: List[ParameterContext]
  alive_generater_dispatcher: List[
    List[Tuple[Union[Generator, AsyncGenerator], bool]]
    # True => async, False => sync
  ]

  @property
  def name(self):
    return self.parameter_contexts[-1].name

  @property
  def annotation(self):
    return self.parameter_contexts[-1].annotation

  @property
  def default(self):
    return self.parameter_contexts[-1].default

  @property
  def _index(self):
    return self.execution_contexts[-1]._index

  @property
  def global_dispatchers(self):
    return self.execution_contexts[0].dispatchers

  @property
  def dispatchers(self):
    return as_sliceable(itertools.chain(
      self.execution_contexts[0].dispatchers,
      self.parameter_contexts[-1].dispatchers,
      self.execution_contexts[-1].dispatchers
    ))

  @property
  def event(self):
    return self.execution_contexts[-1].event

  # dispatcher 允许任何值, 包括 Decorater, 只不过 Decorater Dispatcher 的优先级是隐式最高, 所以基本上不可能截获到.

  def __init__(self, broadcast_instance: "Broadcast"):
    self.broadcast = broadcast_instance
    self.alive_generater_dispatcher = [[]]
    self.parameter_contexts = [ParameterContext(None, None, None, [])]
    self.execution_contexts = [ExecutionContext([], EmptyEvent())]
  
  def enter_context(self, event: BaseEvent, dispatchers: List[BaseDispatcher], use_inline_generator: bool = False):
    self.execution_contexts.append(ExecutionContext(dispatchers, event, use_inline_generator))
    for i in self.dispatchers[self._index:]:
      if getattr(i, "always", False):
        self.execution_contexts[-1].always_dispatchers.add(i)
    return self

  async def __aenter__(self) -> "DispatcherInterface":
    self.alive_generater_dispatcher.append([])
    return self

  async def __aexit__(self, _, exc, tb):
    if self.alive_generater_dispatcher[-1]:
      if self.execution_contexts[-1].inline_generator:
        if len(self.alive_generater_dispatcher) > 2: # 防止插入到保护区
          self.alive_generater_dispatcher[-2].extend(self.alive_generater_dispatcher[-1])
        else:
          raise ValueError("cannot cast to inline")
      else:
        await self.alive_dispatcher_killer()
    self.alive_generater_dispatcher.pop()

    for i in self.dispatchers:
      after_execute_call = getattr(i, "after_execute", None)
      if callable(after_execute_call):
        try:
          await run_always_await_safely(after_execute_call)
        except:
          pass

    self.execution_contexts.pop()

    if tb is not None:
      raise exc

  def inject_local_dispatcher(self, *dispatchers: List[Union[BaseDispatcher, Callable]]):
    for dispatcher in dispatchers[::-1]:
      self.parameter_contexts[-1].dispatchers.insert(0, dispatcher)
    always_dispatchers = self.execution_contexts[-1].always_dispatchers

    for i in dispatchers:
      if getattr(i, "always", False):
        always_dispatchers.add(i)

  def inject_execute_dispatcher(self, *dispatchers: List[Union[BaseDispatcher, Callable]]):
    for dispatcher in dispatchers:
      self.execution_contexts[-1].dispatchers.insert(0, dispatcher)
    always_dispatchers = self.execution_contexts[-1].always_dispatchers

    for i in dispatchers:
      if getattr(i, "always", False):
        always_dispatchers.add(i)

  def inject_global_dispatcher(self, *dispatchers: List[Union[BaseDispatcher, Callable]]):
    #self.dispatchers.extend(dispatchers)
    for dispatcher in dispatchers[::-1]:
      self.global_dispatchers.insert(1, dispatcher)
    always_dispatchers = self.execution_contexts[-1].always_dispatchers

    for i in dispatchers:
      if getattr(i, "always", False):
        always_dispatchers.add(i)

  async def execute_with(self, name: str, annotation, default):
    optional = False
    if isinstance(annotation, _GenericAlias):
      if annotation.__origin__ is Union and annotation.__args__[-1] is type(None):
        # 如果是 Optional, 则它的最后一位应为 NoneType.
        optional = True
        annotation = annotation.__args__[0]
      else:
        raise TypeError("cannot parse this annotation: {0}".format(annotation))

    self.parameter_contexts.append(
      ParameterContext(name, annotation, default, [], optional=optional)
    )

    alive_dispatchers = self.alive_generater_dispatcher[-1]
    always_dispatcher = self.execution_contexts[-1].always_dispatchers
    
    result = None
    try:
      for self.execution_contexts[-1]._index, dispatcher in enumerate(
          self.dispatchers[self._index+int(bool(self._index)):],
          start=self._index+int(bool(self._index))):
        
        if getattr(dispatcher, "always", False) and dispatcher in always_dispatcher: # 你永远不知道需求有多复杂.
          always_dispatcher.remove(dispatcher)

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
          result = await run_always_await_safely(local_dispatcher, self)

        if result is None:
          continue
        
        if result.__class__ is Force:
          result = result.target

        self.execution_contexts[-1]._index = 0
        return result
      else:
        if optional:
          self.execution_contexts[-1]._index = 0
          return None
        raise RequirementCrashed("the dispatching requirement crashed: ", self.name, self.annotation, self.default)
    finally:
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
          await run_always_await_safely(local_dispatcher, self)

      self.parameter_contexts.pop()

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
