from abc import ABCMeta, abstractmethod, abstractproperty, abstractstaticmethod
from typing import Any, AsyncGenerator, Generator, List, Optional, Tuple, Union
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import BaseEvent

from graia.broadcast.typing import T_Dispatcher, T_Dispatcher_Callable


class IDispatcherInterface(metaclass=ABCMeta):
    broadcast: "Broadcast"

    execution_contexts: List["ExecutionContext"]
    parameter_contexts: List["ParameterContext"]
    alive_generator_dispatcher: List[
        List[Tuple[Union[Generator, AsyncGenerator], bool]]
    ]

    @abstractmethod
    def start_execution(
        self,
        event: BaseEvent,
        dispatchers: List[T_Dispatcher],
        use_inline_generator: bool = False,
    ):
        pass

    @abstractmethod
    async def exit_current_execution(self):
        pass

    @abstractmethod
    async def alive_dispatcher_killer(self):
        pass

    def inject_local_raw(self, *dispatchers: List[T_Dispatcher], source: Any = None):
        for dispatcher in dispatchers[::-1]:
            self.parameter_contexts[-1].dispatchers.insert(0, dispatcher)
        always_dispatchers = self.execution_contexts[-1].always_dispatchers

        for i in dispatchers:
            if getattr(i, "always", False):
                always_dispatchers.add(i)

    def inject_execution_raw(self, *dispatchers: List[T_Dispatcher]):
        for dispatcher in dispatchers:
            self.execution_contexts[-1].dispatchers.insert(0, dispatcher)
        always_dispatchers = self.execution_contexts[-1].always_dispatchers

        for i in dispatchers:
            if getattr(i, "always", False):
                always_dispatchers.add(i)

    def inject_global_raw(self, *dispatchers: List[T_Dispatcher]):
        # self.dispatchers.extend(dispatchers)
        for dispatcher in dispatchers[::-1]:
            self.execution_contexts[0].dispatchers.insert(1, dispatcher)
        always_dispatchers = self.execution_contexts[-1].always_dispatchers

        for i in dispatchers:
            if getattr(i, "always", False):
                always_dispatchers.add(i)

    @abstractproperty
    def dispatcher_sources(self) -> List["DispatcherSource"]:
        pass

    @abstractmethod
    def dispatcher_pure_generator(self) -> Generator[None, None, T_Dispatcher]:
        pass

    @abstractmethod
    def dispatcher_generator(
        self,
    ) -> Generator[None, None, Tuple[T_Dispatcher, T_Dispatcher_Callable, Any]]:
        pass

    @abstractproperty
    def name(self) -> str:
        pass

    @abstractproperty
    def annotation(self) -> Any:
        pass

    @abstractproperty
    def default(self) -> Any:
        pass

    @abstractproperty
    def _index(self) -> int:
        pass

    @abstractproperty
    def global_dispatcher(self) -> List[T_Dispatcher]:
        pass

    @abstractproperty
    def event(self) -> BaseEvent:
        pass

    @abstractmethod
    async def execute_dispatcher_callable(
        self, dispatcher_callable: T_Dispatcher_Callable
    ) -> Any:
        pass

    @abstractmethod
    async def lookup_param(self, name: str, annotation: Any, default: Any) -> Any:
        pass

    @abstractmethod
    async def lookup_using_current(self) -> Any:
        pass

    @abstractmethod
    async def lookup_by(
        self, dispatcher: T_Dispatcher, name: str, annotation: Any, default: Any
    ) -> Any:
        pass

    @abstractmethod
    async def lookup_by_directly(
        self, dispatcher: T_Dispatcher, name: str, annotation: Any, default: Any
    ) -> Any:
        pass

    @abstractproperty
    def has_current_exec_context(self) -> bool:
        pass

    @abstractproperty
    def has_current_param_context(self) -> bool:
        pass


from graia.broadcast.entities.source import DispatcherSource
from graia.broadcast.entities.context import ExecutionContext, ParameterContext
