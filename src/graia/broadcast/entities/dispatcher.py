from abc import ABCMeta, abstractstaticmethod
from types import TracebackType
from typing import List, Optional


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

    def afterExecution(
        self,
        interface: "IDispatcherInterface",
        exception: Optional[Exception],
        tb: Optional[TracebackType],
    ):
        pass

    def beforeTargetExec(self, interface: "IDispatcherInterface"):
        pass

    def afterTargetExec(
        self,
        interface: "IDispatcherInterface",
        exception: Optional[Exception],
        tb: Optional[TracebackType],
    ):
        pass

    def onActive(self, interface: "IDispatcherInterface"):
        pass


from graia.broadcast.abstract.interfaces.dispatcher import IDispatcherInterface
