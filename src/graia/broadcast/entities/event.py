from abc import ABCMeta
from iterwrapper import IterWrapper
from .dispatcher import BaseDispatcher
class EventMeta(ABCMeta):
    def __new__(mcls, name, bases, mapping, **kwargs):
        if any(IterWrapper(bases).filter(lambda x: getattr(x, "__base_event__", False)).collect(list)):
            if not mapping.__contains__("__base_event__"):
                mapping["__base_event__"] = False
        if not mapping.get("Dispatcher") and name != "BaseEvent":
            raise AttributeError("a event class must have a dispatcher called 'Dispatcher'")
        return super().__new__(mcls, name, bases, mapping, **kwargs)

class BaseEvent(metaclass=EventMeta):
    Dispatcher: BaseDispatcher

