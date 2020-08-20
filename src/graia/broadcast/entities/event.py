from iterwrapper import IterWrapper
from pydantic.main import ModelMetaclass

from .dispatcher import BaseDispatcher
import copy

class EventMeta(ModelMetaclass):
    class Config:
        arbitrary_types_allowed = True

    def __new__(mcls, name, bases, mapping, **kwargs):
        if any(IterWrapper(bases).filter(lambda x: getattr(x, "__base_event__", False)).collect(list)):
            if not mapping.__contains__("__base_event__"):
                mapping["__base_event__"] = False
        if not mapping.get("Dispatcher") and name != "BaseEvent":
            raise AttributeError("a event class must have a dispatcher called 'Dispatcher'")
        if not mapping.get("Config") or not getattr(mapping.get("Config"), "arbitrary_types_allowed", False):
            if not mapping.get("Config"):
                mapping['Config'] = copy.copy(mcls.Config)
            else:
                mapping['Config'].arbitrary_types_allowed = True
        r = super().__new__(mcls, name, bases, mapping, **kwargs)
        if mapping.get("type"):
            r.type = mapping.get("type")
        return r

class BaseEvent(metaclass=EventMeta):
    Dispatcher: BaseDispatcher

    def __init__(self, **kwargs):
        super().__init__(**kwargs)