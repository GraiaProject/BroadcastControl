import asyncio
import inspect
import traceback
from typing import Dict, Generator, List, NoReturn, Optional, Type, Union
import types

from iterwrapper import IterWrapper as iw

from .builtin.dispatchers import MappingRule, SimpleMapping
from .builtin.event import ExceptionThrowed
from .entities.decorater import Decorater
from .entities.dispatcher import BaseDispatcher
from .entities.event import BaseEvent
from .entities.inject_rule import BaseRule
from .entities.listener import Listener
from .entities.namespace import Namespace
from .entities.signatures import Force, RemoveMe
from .exceptions import (DisabledNamespace, ExecutionStop, ExistedNamespace,
                         InvaildEventName, PropagationCancelled,
                         RegisteredEventListener, RequirementCrashed,
                         UnexistedNamespace)
from .interfaces.decorater import DecoraterInterface
from .interfaces.dispatcher import DispatcherInterface
from .protocols.executor import ExecutorProtocol
from .utilles import (argument_signature, dispatcher_mixin_handler, group_dict, isasyncgen, isgenerator, run_always_await,
                      whatever_gen_once)


class Broadcast:
  loop: asyncio.AbstractEventLoop

  default_namespace: Namespace
  namespaces: List[Namespace]
  listeners: List[Listener]

  # 规则驱动注入
  dispatcher_inject_rules: List[BaseRule] = []
  
  dispatcher_interface: DispatcherInterface

  debug_flag: bool

  def __init__(self, *, loop: asyncio.AbstractEventLoop = None, debug_flag: bool = False,
    inject_rules: Optional[List[BaseRule]] = None
  ):
    self.loop = loop or asyncio.get_event_loop()
    self.default_namespace = Namespace(name="default", default=True)
    self.debug_flag = debug_flag
    self.namespaces = []
    self.listeners = []
    self.dispatcher_inject_rules = inject_rules or []
    self.dispatcher_interface = DispatcherInterface(self)
  
  def default_listener_generator(self, event_class) -> Listener:
    yield from (iw(self.listeners)
      .filter(lambda x: not x.namespace.hide) # filter for hide
      .filter(lambda x: not x.namespace.disabled) # filter for disabled
      .filter(lambda x: event_class in x.listening_events)
      .collect(list) # collect to a whole list
    )

  def addInjectionRule(self, rule: BaseRule) -> NoReturn:
    if rule in self.dispatcher_inject_rules:
      raise ValueError("this rule has already been added!")
    self.dispatcher_inject_rules.append(rule)
  
  def removeInjectionRule(self, rule: BaseRule) -> NoReturn:
    self.dispatcher_inject_rules.remove(rule)

  async def layered_scheduler(self,
    listener_generator: Generator[Listener, None, None],
    event: BaseEvent
  ):
    grouped: Dict[int, List[Listener]] = group_dict(listener_generator, lambda x: x.priority)
    break_flag = False
    for current_priority in sorted(grouped.keys()):
      if break_flag:
        break
      current_group = grouped[current_priority]
      tasks, _ = await asyncio.wait([
        self.Executor(ExecutorProtocol(
          target=i,
          event=event
        )) for i in current_group
      ])
      for i in list(tasks):
        if isinstance(i.exception(), PropagationCancelled):
          break_flag = True

  async def Executor(self, protocol: ExecutorProtocol):
    is_listener = isinstance(protocol.target, Listener)

    if is_listener:
      if protocol.target.namespace.disabled:
        raise DisabledNamespace("catched a disabled namespace: {0}".format(protocol.target.namespace.name))

    # 先生成 dispatchers
    dispatchers = dispatcher_mixin_handler(protocol.event.Dispatcher)
    # 开始暴力注入
    if is_listener:
      if protocol.target.inline_dispatchers:
        dispatchers = protocol.target.inline_dispatchers + dispatchers
      if protocol.target.namespace.injected_dispatchers:
        dispatchers = protocol.target.namespace.injected_dispatchers + dispatchers
    if protocol.dispatchers:
      dispatchers = protocol.dispatchers + dispatchers

    target_callable = protocol.target.callable if is_listener else protocol.target
    parameter_compile_result = {}

    async with self.dispatcher_interface.enter_context(protocol.event, dispatchers) as dii:
      if (not dii.dispatchers) or type(dii.dispatchers[0]) is not DecoraterInterface:
        DecoraterInterface(dii)  # pylint: disable=unused-variable
      # Decorater 的 Dispatcher 已经注入, 没他事了

      if protocol.enableInternalAccess or \
        (is_listener and \
          protocol.target.enable_internal_access):
        internal_access_mapping = {
          Broadcast: self,
          ExecutorProtocol: protocol,
          DispatcherInterface: dii,
          **({ # 当 protocol.target 为 Listener 时的特有解析
            Listener: protocol.target,
            Namespace: protocol.target.namespace
          } if is_listener else {})
        }
        @dii.inject_global_dispatcher
        def _(interface: DispatcherInterface):
          return internal_access_mapping.get(interface.annotation)

      for injection_rule in self.dispatcher_inject_rules:
        if injection_rule.check(protocol.event, dii):
          dii.dispatchers.insert(1, injection_rule.target_dispatcher)

      @dii.inject_global_dispatcher
      def _(interface: DispatcherInterface):
        if interface.annotation is protocol.event.__class__:
          return protocol.event

      try:
        for name, annotation, default in argument_signature(target_callable):
          parameter_compile_result[name] =\
            await dii.execute_with(name, annotation, default)
        if is_listener:
          if protocol.target.headless_decoraters: # 无头装饰器
            for hl_d in protocol.target.headless_decoraters:
              await dii.execute_with(None, None, hl_d)
      except ExecutionStop:
        raise
      except RequirementCrashed:
        traceback.print_exc()
        raise
      except Exception as e:
        traceback.print_exc()
        if not protocol.hasReferrer: # 如果没有referrer, 会广播事件, 如果有则向上抛出
          self.postEvent(ExceptionThrowed(
            exception=e,
            event=protocol.event
          ))
        raise

      try:
        result = await run_always_await(
          target_callable(**parameter_compile_result)
        )
      except ExecutionStop:
        raise # 直接抛出.
      except PropagationCancelled:
        raise # 防止事件广播
      except Exception as e:
        traceback.print_exc()
        if not protocol.hasReferrer: # 如果没有referrer, 则广播事件, 如果有则向上抛出(防止重复抛出事件)
          self.postEvent(ExceptionThrowed(
            exception=e,
            event=protocol.event
          ))
        raise

      if isgenerator(result) or isasyncgen(result):
        dii.alive_generater_dispatcher[-1].append(result)
        result = await whatever_gen_once(result)

      if result.__class__ is Force:
        return result.content

      if result.__class__ is RemoveMe:
        if is_listener:
          if protocol.target in self.listeners:
            self.listeners.pop(self.listeners.index(protocol.target))
      return result

  def postEvent(self, event: BaseEvent):
    self.loop.create_task(self.layered_scheduler(
      listener_generator=self.default_listener_generator(event.__class__),
      event=event
    ))

  @staticmethod
  def event_class_generator(target=BaseEvent):
    for i in target.__subclasses__():
      yield i
      if i.__subclasses__():
        yield from Broadcast.event_class_generator(i)

  @staticmethod
  def findEvent(name: str):
    for i in Broadcast.event_class_generator():
      if i.__name__ == name:
        return i

  def getDefaultNamespace(self):
    return self.default_namespace
  
  def createNamespace(self, name, *, priority: int = 0, hide: bool = False, disabled: bool = False):
    if self.containNamespace(name):
      raise ExistedNamespace(name, "has been created!")
    self.namespaces.append(Namespace(name=name, priority=priority, hide=hide, disabled=disabled))
    return self.namespaces[-1]
  
  def removeNamespace(self, name):
    if self.containNamespace(name):
      for index, i in enumerate(self.namespaces):
        if i.name == name:
          self.namespaces.pop(index)
          return
    else:
      raise UnexistedNamespace(name)

  def containNamespace(self, name):
    for i in self.namespaces:
      if i.name == name:
        return True
    return False
  
  def getNamespace(self, name):
    if self.containNamespace(name):
      for i in self.namespaces:
        if i.name == name:
          return i
    else:
      raise UnexistedNamespace(name)

  def hideNamespace(self, name):
    ns = self.getNamespace(name)
    ns.hide = True

  def unhideNamespace(self, name):
    ns = self.getNamespace(name)
    ns.hide = False

  def disableNamespace(self, name):
    ns = self.getNamespace(name)
    ns.disabled = True

  def enableNamespace(self, name):
    ns = self.getNamespace(name)
    ns.disabled = False

  def containListener(self, target):
    for i in self.listeners:
      if i.callable == target:
        return True
    return False

  def getListener(self, target):
    for i in self.listeners:
      if i.callable == target:
        return i

  def removeListener(self, target):
    self.listeners.remove(target)

  def receiver(self,
      event: Union[str, Type[BaseEvent]],
      priority: int = 16,
      dispatchers: List[Type[BaseDispatcher]] = [],
      namespace: Namespace = None,
      headless_decoraters: List[Decorater] = [],
      enable_internal_access: bool = False
  ):
    if isinstance(event, str):
      _name = event
      event = self.findEvent(event)
      if not event:
        raise InvaildEventName(_name, "is not vaild!")
    priority = (type(priority) == int) and priority or int(priority) # 类型转换
    def receiver_wrapper(callable_target):
      may_listener = self.getListener(callable_target)
      if not may_listener:
        self.listeners.append(Listener(
          callable=callable_target,
          namespace=namespace or self.getDefaultNamespace(),
          inline_dispatchers=dispatchers,
          priority=priority,
          listening_events=[event],
          headless_decoraters=headless_decoraters,
          enable_internal_access=enable_internal_access
        ))
      else:
        if event not in may_listener.listening_events:
          may_listener.listening_events.append(event)
        else:
          raise RegisteredEventListener(event.__name__, "has been registered!")
      return callable_target
    return receiver_wrapper
