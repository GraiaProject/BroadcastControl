from typing import Any, Callable, List

from pydantic import BaseModel  # pylint: disable=no-name-in-module

from ..entities.dispatcher import BaseDispatcher
from ..entities.signatures import Force
from ..interfaces.dispatcher import DispatcherInterface


class MappingRule(BaseModel):
    mode: Callable[[DispatcherInterface], bool]
    value: Any

    @classmethod
    def nameEquals(cls, name, value):
        return cls(mode=lambda x: x.name == name, value=value)

    @classmethod
    def annotationEquals(cls, annotation, value):
        return cls(mode=lambda x: x.annotation == annotation, value=value)

    @classmethod
    def defaultEquals(cls, default, value):
        return cls(mode=lambda x: x.default == default, value=value)

def SimpleMapping(rules: List[MappingRule]):
    class mapping_dispatcher(BaseDispatcher):
        @staticmethod
        def catch(interface: DispatcherInterface):
            for rule in rules:
                if rule.mode(interface):
                    return Force(rule.value)
    return mapping_dispatcher

def Hook(condition, fixer):
    class hook_dispatcher(BaseDispatcher):
        @staticmethod
        def catch(interface: DispatcherInterface):
            if condition(interface):
                return fixer(interface.execute_with(
                    interface.name,
                    interface.annotation,
                    interface.default
                ))
    return hook_dispatcher