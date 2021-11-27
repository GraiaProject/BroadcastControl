from abc import ABCMeta, abstractmethod
from types import TracebackType
from typing import List, Optional, Type, Union

from ..interfaces.dispatcher import DispatcherInterface as DispatcherInterface

class BaseDispatcher(metaclass=ABCMeta):
    mixin: List[Union[BaseDispatcher, Type[BaseDispatcher]]]
    @abstractmethod
    async def catch(self, interface: DispatcherInterface): ...
    def beforeExecution(self, interface: DispatcherInterface): ...
    def afterDispatch(
        self,
        interface: DispatcherInterface,
        exception: Optional[Exception],
        tb: Optional[TracebackType],
    ): ...
    def afterExecution(
        self,
        interface: DispatcherInterface,
        exception: Optional[Exception],
        tb: Optional[TracebackType],
    ): ...
