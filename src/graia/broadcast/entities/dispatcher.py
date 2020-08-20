from abc import ABCMeta, abstractstaticmethod
from typing import List

class BaseDispatcher(metaclass=ABCMeta):
    always: bool
    mixin: List["BaseDispatcher"]

    @abstractstaticmethod
    def catch(interface: "DispatcherInterface"):
        pass

    @staticmethod
    def check(interface: "DispatcherInterface"):
        return True
