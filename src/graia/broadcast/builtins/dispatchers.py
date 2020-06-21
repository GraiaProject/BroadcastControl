from ..entities.dispatcher import BaseDispatcher
from ..interfaces.dispatcher import DispatcherInterface
from ..entities.signatures import Force
from pydantic import BaseModel # pylint: disable=no-name-in-module
from typing import Callable, Any, List

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