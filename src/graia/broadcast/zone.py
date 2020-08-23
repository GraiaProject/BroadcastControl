from typing import List, NoReturn, Optional, Type, Union

from .entities.inject_rule import BaseRule
from .entities.decorater import Decorater
from .entities.dispatcher import BaseDispatcher
from .entities.event import BaseEvent
from .exceptions import InvaildEventName, RegisteredEventListener
from .entities.namespace import Namespace
from .entities.listener import Listener

class Zone:
    namespace: Namespace
    listeners: List[Listener]
    dispatcher_inject_rules: List[BaseRule]

    def __init__(self, name: str, priority: Optional[int] = None,
        injected_dispatchers: Optional[List[BaseDispatcher]] = None
    ) -> None:
        self.namespace = Namespace(
            name=name,
            priority=priority,
            injected_dispatchers=injected_dispatchers or []
        )
        self.listeners = []
        self.dispatcher_inject_rules = []
    
    @staticmethod
    def event_class_generator(target=BaseEvent):
        for i in target.__subclasses__():
          yield i
          if i.__subclasses__():
            yield from Zone.event_class_generator(i)
    
    @staticmethod
    def findEvent(name: str):
        for i in Zone.event_class_generator():
          if i.__name__ == name:
            return i
    
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
                    namespace=self.namespace,
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

    def addInjectionRule(self, rule: BaseRule) -> NoReturn:
        if rule in self.dispatcher_inject_rules:
            raise ValueError("this rule has already been added!")
        self.dispatcher_inject_rules.append(rule)
    
    def removeInjectionRule(self, rule: BaseRule) -> NoReturn:
        self.dispatcher_inject_rules.remove(rule)