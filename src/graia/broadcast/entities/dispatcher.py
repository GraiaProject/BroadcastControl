from abc import ABCMeta, abstractstaticmethod
from typing import List


class BaseDispatcher(metaclass=ABCMeta):
    always: bool
    mixin: List["BaseDispatcher"]

    @abstractstaticmethod
    def catch(interface: "IDispatcherInterface"):
        pass

    def beforeDispatch(self, interface: "IDispatcherInterface"):
        pass

    def afterDispatch(self, interface: "IDispatcherInterface"):
        pass

    def beforeExecution(self, interface: "IDispatcherInterface"):
        pass

    def afterExecution(self, interface: "IDispatcherInterface"):
        pass

    def onActive(self, interface: "IDispatcherInterface"):
        pass


from graia.broadcast.abstract.interfaces.dispatcher import IDispatcherInterface
