from abc import ABCMeta, abstractmethod, abstractproperty, abstractstaticmethod
from functools import lru_cache
from inspect import ismethod
import traceback
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
)

from graia.broadcast.utilles import run_always_await_safely, cached_getattr

DEFAULT_LIFECYCLE_NAMES = (
    "beforeDispatch",
    "afterDispatch",
    "beforeExecution",
    "afterExecution",
    "beforeTargetExec",
    "afterTargetExec",
)


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
        event: "BaseEvent",
        dispatchers: List["T_Dispatcher"],
        use_inline_generator: bool = False,
    ):
        pass

    @abstractmethod
    async def exit_current_execution(self):
        pass

    @abstractmethod
    async def alive_dispatcher_killer(self):
        pass

    def inject_local_raw(self, *dispatchers: List["T_Dispatcher"], source: Any = None):
        # 为什么没有 flush: 因为这里的 lifecycle 是无意义的.
        for dispatcher in dispatchers[::-1]:
            self.parameter_contexts[-1].dispatchers.insert(0, dispatcher)
        always_dispatchers = self.execution_contexts[-1].always_dispatchers

        for i in dispatchers:
            if cached_getattr(i, "always", False):
                always_dispatchers.add(i)

    def inject_execution_raw(self, *dispatchers: List["T_Dispatcher"]):
        for dispatcher in dispatchers:
            self.execution_contexts[-1].dispatchers.insert(0, dispatcher)
        always_dispatchers = self.execution_contexts[-1].always_dispatchers

        self.flush_lifecycle_refs(dispatchers)
        for i in dispatchers:
            if cached_getattr(i, "always", False):
                always_dispatchers.add(i)

    def inject_global_raw(self, *dispatchers: List["T_Dispatcher"]):
        # self.dispatchers.extend(dispatchers)
        for dispatcher in dispatchers[::-1]:
            self.execution_contexts[0].dispatchers.insert(1, dispatcher)
        always_dispatchers = self.execution_contexts[-1].always_dispatchers

        self.flush_lifecycle_refs(dispatchers)
        for i in dispatchers:
            if cached_getattr(i, "always", False):
                always_dispatchers.add(i)

    @staticmethod
    @lru_cache
    def get_lifecycle_refs(
        dispatcher: "T_Dispatcher",
    ) -> Optional[Dict[str, List]]:
        from graia.broadcast.entities.dispatcher import BaseDispatcher

        lifecycle_refs: Dict[str, List] = {}
        if not isinstance(dispatcher, (BaseDispatcher, type)):
            return

        for name in DEFAULT_LIFECYCLE_NAMES:
            lifecycle_refs.setdefault(name, [])
            abstract_lifecycle_func = cached_getattr(BaseDispatcher, name)
            unbound_attr = getattr(dispatcher, name, None)

            if unbound_attr is None:
                continue

            orig_call = unbound_attr
            while ismethod(orig_call):
                orig_call = unbound_attr.__func__

            if orig_call is abstract_lifecycle_func:
                continue

            lifecycle_refs[name].append(unbound_attr)

        return lifecycle_refs

    def flush_lifecycle_refs(
        self,
        dispatchers: List["T_Dispatcher"] = None,
    ):
        from graia.broadcast.entities.dispatcher import BaseDispatcher

        lifecycle_refs = self.execution_contexts[-1].lifecycle_refs
        if dispatchers is None and lifecycle_refs:  # 已经刷新.
            return

        for dispatcher in dispatchers or self.dispatcher_pure_generator():
            if (
                not isinstance(dispatcher, BaseDispatcher)
                or dispatcher.__class__ is type
            ):
                continue

            for name, value in self.get_lifecycle_refs(dispatcher).items():
                lifecycle_refs.setdefault(name, [])
                lifecycle_refs[name].extend(value)

    async def exec_lifecycle(self, lifecycle_name: str, *args, **kwargs):
        lifecycle_funcs = self.execution_contexts[-1].lifecycle_refs.get(
            lifecycle_name, []
        )
        if lifecycle_funcs:
            for func in lifecycle_funcs:
                await run_always_await_safely(func, self, *args, **kwargs)

    @abstractproperty
    def dispatcher_sources(self) -> List["DispatcherSource"]:
        pass

    @abstractmethod
    def dispatcher_pure_generator(self) -> Generator[None, None, "T_Dispatcher"]:
        pass

    @abstractmethod
    def dispatcher_generator(
        self,
    ) -> Generator[None, None, Tuple["T_Dispatcher", "T_Dispatcher_Callable", Any]]:
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
    def global_dispatcher(self) -> List["T_Dispatcher"]:
        pass

    @abstractproperty
    def event(self) -> "BaseEvent":
        pass

    @abstractmethod
    async def execute_dispatcher_callable(
        self, dispatcher_callable: "T_Dispatcher_Callable"
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
        self, dispatcher: "T_Dispatcher", name: str, annotation: Any, default: Any
    ) -> Any:
        pass

    @abstractmethod
    async def lookup_by_directly(
        self, dispatcher: "T_Dispatcher", name: str, annotation: Any, default: Any
    ) -> Any:
        pass

    @abstractproperty
    def has_current_exec_context(self) -> bool:
        pass

    @abstractproperty
    def has_current_param_context(self) -> bool:
        pass


from graia.broadcast.typing import T_Dispatcher, T_Dispatcher_Callable
from graia.broadcast.entities.context import ExecutionContext, ParameterContext
from graia.broadcast.entities.source import DispatcherSource
from graia.broadcast.entities.event import BaseEvent
