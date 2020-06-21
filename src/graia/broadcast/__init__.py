import asyncio
from typing import Any, AsyncGenerator, Generator, List

from iterwrapper import IterWrapper as iw

from .builtins.dispatchers import MappingRule, SimpleMapping
from .builtins.event import ExceptionThrowed
from .entities.decorater import Decorater
from .entities.event import BaseEvent
from .entities.listener import Listener
from .entities.namespace import Namespace
from .entities.signatures import Force, RemoveMe
from .exceptions import DisabledNamespace, RequirementCrashed
from .interfaces.decorater import DecoraterInterface
from .interfaces.dispatcher import DispatcherInterface
from .protocols.executor import ExecutorProtocol
from .utilles import argument_signature, iw_group, printer, run_always_await


class Broadcast:
  loop: asyncio.AbstractEventLoop
  event_queue: asyncio.Queue

  default_namespace: Namespace
  namespaces: List[Namespace] = []
  listeners: List[Listener] = []

  stoped: bool = False

  def __init__(self, *, loop: asyncio.AbstractEventLoop = None, queue: asyncio.Queue = None):
    self.loop = loop or asyncio.get_event_loop()
    self.event_queue = queue or asyncio.Queue(15, loop=self.loop)
    self.default_namespace = Namespace(name="default", default=True)

  async def event_generator(self) -> AsyncGenerator[Any, BaseEvent]:
      while True:
        try:
          yield await asyncio.wait_for(self.event_queue.get(), timeout=5)
        except asyncio.TimeoutError:
          continue
        except asyncio.CancelledError:
          return
  
  def listener_generator(self, event_class) -> Listener:
    yield from (iw_group(iw(self.listeners)
      .filter(lambda x: not x.namespace.hide) # filter for hide
      .filter(lambda x: not x.namespace.disabled) # filter for disabled
      .filter(lambda x: event_class in x.listening_events),
        key=lambda x: x.namespace.name # group
      ).map(lambda x: iw(x).apply(list.sort, key=lambda x: x.priority).collect(list)) # sort in group
      .flat() # unpack
      .collect(list) # collect to a whole list
    )

  async def event_runner(self):
    async for event in self.event_generator():
      for listener in self.listener_generator(event.__class__):
        self.loop.create_task(self.Executor(ExecutorProtocol(
          target=listener,
          event=event
        )))
      
  async def Executor(self, protocol: ExecutorProtocol):
    if isinstance(protocol.target, Listener):
      if protocol.target.namespace.disabled:
        raise DisabledNamespace("catched a disabled namespace: {0}".format(protocol.target.namespace.name))

    # 先生成 dispatchers
    dispatchers = DispatcherInterface.dispatcher_mixin_handler(protocol.event.Dispatcher)
    # 开始暴力注入
    if isinstance(protocol.target, Listener):
      if protocol.target.inline_dispatchers:
        dispatchers = protocol.target.inline_dispatchers + dispatchers
      if protocol.target.namespace.injected_dispatchers:
        dispatchers = protocol.target.namespace.injected_dispatchers + dispatchers
    if protocol.dispatchers:
      dispatchers = protocol.dispatchers + dispatchers

    target_callable = protocol.target.callable if isinstance(protocol.target, Listener) else protocol.target
    parameter_compile_result = {}

    async with DispatcherInterface(self, protocol.event, dispatchers) as dii:
      dei = DecoraterInterface(dii)  # pylint: disable=unused-variable
      # Decorater 的 Dispatcher 已经注入, 没他事了

      dii.dispatchers.append(SimpleMapping([
        MappingRule.annotationEquals(Broadcast, self),
        MappingRule.annotationEquals(ExecutorProtocol, protocol),
        MappingRule.annotationEquals(DispatcherInterface, dii),
        *([ # 当 protocol.target 为 Listener 时的特有解析
          MappingRule.annotationEquals(Listener, protocol.target),
          MappingRule.annotationEquals(Namespace, protocol.target.namespace)
        ] if isinstance(protocol.target, Listener) else []),
      ]))
      try:
        for name, annotation, default in argument_signature(target_callable):
          parameter_compile_result[name] =\
            await dii.execute_with(name, annotation, default)
      except RequirementCrashed:
            raise
      except Exception as e:
        import traceback
        traceback.print_exc()
        if not protocol.hasReferrer:
          await self.postEvent(ExceptionThrowed(
            exception=e,
            event=protocol.event
          ))
        else:
          raise

      result = await run_always_await(
        target_callable(**parameter_compile_result)
      )
      if isinstance(result, Force):
        return result.content

      if isinstance(result, RemoveMe):
        if isinstance(protocol.target, Listener):
          if protocol.target in self.listeners:
            self.listeners.pop(self.listeners.index(protocol.target))
      return result

  async def postEvent(self, event: BaseEvent):
    await self.event_queue.put(event)
