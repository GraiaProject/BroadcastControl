import weakref
import itertools

from pydantic.errors import NoneIsAllowedError

from graia.broadcast.abstract.interfaces.dispatcher import IDispatcherInterface
from typing import Any, AsyncGenerator, Callable, Generator, Iterator, List, Optional, Tuple, Union, _GenericAlias
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import BaseEvent

from graia.broadcast.entities.context import ExecutionContext, ParameterContext
from graia.broadcast.entities.signatures import Force
from graia.broadcast.entities.source import DispatcherSource
from graia.broadcast.exceptions import OutOfMaxGenerater, RequirementCrashed
from graia.broadcast.typing import T_Dispatcher, T_Dispatcher_Callable
from graia.broadcast.utilles import is_asyncgener, isgeneratorfunction, run_always_await_safely

class EmptyEvent(BaseEvent):
    class Dispatcher:
        @staticmethod
        def catch(_):
            pass

class DispatcherInterface(IDispatcherInterface):
    @property
    def name(self) -> str:
        return self.parameter_contexts[-1].name
    
    @property
    def annotation(self) -> Any:
        return self.parameter_contexts[-1].annotation
    
    @property
    def default(self) -> Any:
        return self.parameter_contexts[-1].default
    
    @property
    def _index(self) -> int:
        return self.execution_contexts[-1]._index
    
    @property
    def event(self) -> BaseEvent:
        return self.execution_contexts[-1].event

    @property
    def global_dispatcher(self) -> List[T_Dispatcher]:
        return self.execution_contexts[0].dispatchers
    
    @property
    def has_current_exec_context(self) -> bool:
        return len(self.execution_contexts) >= 2
    
    @property
    def has_current_param_context(self) -> bool:
        return len(self.parameter_contexts) >= 2

    def __init__(self, broadcast_instance: "Broadcast") -> None:
        self.broadcast = broadcast_instance
        self.alive_generator_dispatcher = [[]]
        self.execution_contexts = [ExecutionContext([], EmptyEvent())]
        self.parameter_contexts = [ParameterContext(None, None, None, [])]

    async def __aenter__(self) -> "DispatcherInterface":
        return self
    
    async def __aexit__(self, _, exc: Exception, tb):
        await self.exit_current_execution()
        if tb is not None:
            raise exc.with_traceback(tb)

    def start_execution(self, event: BaseEvent, dispatchers: List[T_Dispatcher], use_inline_generator: bool = False) -> "DispatcherInterface":
        current_exec_context = ExecutionContext(dispatchers, event, use_inline_generator)
        # 这里本来应该要让所有 always 集中下的......因为性能实在是太过惨淡, 故放弃
        self.execution_contexts.append(current_exec_context)
        self.alive_generator_dispatcher.append([])
        return self
    
    async def exit_current_execution(self):
        if self.alive_generator_dispatcher[-1]:
          if self.execution_contexts[-1].inline_generator:
            if len(self.alive_generator_dispatcher) > 2: # 防止插入到保护区
              self.alive_generator_dispatcher[-2].extend(self.alive_generator_dispatcher[-1])
            else:
              raise ValueError("cannot cast to inline")
          else:
            await self.alive_dispatcher_killer()
        self.alive_generator_dispatcher.pop()

        for i in self.dispatcher_pure_generator():
            after_execute_call = getattr(i, "after_execute", None)
            if callable(after_execute_call):
                try:
                    await run_always_await_safely(after_execute_call)
                except:
                    pass
        
        self.execution_contexts.pop()
    
    async def alive_dispatcher_killer(self):
        for unbound_gen, is_async_gen in self.alive_generator_dispatcher[-1]:
            index = 0
            if is_async_gen:
                async for _ in unbound_gen:
                    if index == 15:
                        raise OutOfMaxGenerater("a dispatch as a sync generator had to stop: ", unbound_gen)
                    index += 1
            else:
                for _ in unbound_gen:
                    if index == 15:
                        raise OutOfMaxGenerater("a dispatch as a sync generator had to stop: ", unbound_gen)
                    index += 1
    
    @property
    def dispatcher_sources(self) -> List[DispatcherSource]:
        return [
            self.execution_contexts[0].source,
            self.parameter_contexts[-1].source,
            self.execution_contexts[-1].source
        ]
    
    def dispatcher_pure_generator(self) -> Generator[None, None, T_Dispatcher]:
        for source in self.dispatcher_sources:
            yield from source.dispatchers
    
    def dispatcher_generator(self, 
        source_from: Callable[["DispatcherInterface"], Iterator[DispatcherSource[T_Dispatcher, Any]]] = \
            lambda x: x.dispatcher_sources
    ) -> Generator[None, None, Tuple[T_Dispatcher, T_Dispatcher_Callable, DispatcherSource]]:
        always_dispatcher = self.execution_contexts[-1].always_dispatchers
        
        for source in source_from(self):
            for dispatcher in source.dispatchers:
                if dispatcher in always_dispatcher:
                    always_dispatcher.remove(dispatcher)
                
                dispatcher_callable: T_Dispatcher_Callable = None
                if dispatcher.__class__ is type and issubclass(dispatcher, BaseDispatcher):
                    dispatcher_callable = dispatcher().catch
                elif hasattr(dispatcher, "catch"):
                    dispatcher_callable = dispatcher.catch
                elif callable(dispatcher):
                    dispatcher_callable = dispatcher
                else:
                    raise ValueError("invaild dispatcher: ", dispatcher)
                
                yield (dispatcher, dispatcher_callable, source)

    async def execute_dispatcher_callable(self, dispatcher_callable: T_Dispatcher_Callable) -> Any:
        alive_dispatchers = self.alive_generator_dispatcher[-1]

        if is_asyncgener(dispatcher_callable):
            current_generator = dispatcher_callable(self).__aiter__()

            try:
                result = await current_generator.__anext__()
            except StopAsyncIteration:
                return
            else:
                alive_dispatchers.append((current_generator, True))
        elif isgeneratorfunction(dispatcher_callable):
            current_generator = dispatcher_callable(self).__iter__()

            try:
                result = current_generator.__next__()
            except StopIteration as e:
                result = e.value
            else:
                alive_dispatchers.append((current_generator, False))
        else:
            result = await run_always_await_safely(dispatcher_callable, self)
        
        return result

    @staticmethod
    def preprocess_param_annotation(annotation: Any) -> Tuple[Any, bool]:
        optional = False
        if isinstance(annotation, _GenericAlias):
            if annotation.__origin__ is Union and annotation.__args__[-1] is type(None):
                # 如果是 Optional, 则它的最后一位应为 NoneType.
                optional = True
                annotation = annotation.__args__[0]
            else:
                raise TypeError("cannot preprocess this annotation: {0}".format(annotation))

        return (annotation, optional)

    async def lookup_param(self,
        name: str, annotation: Any, default: Any,
        enable_extra_return: bool = False
    ) -> Union[Any, Tuple[Any, T_Dispatcher, DispatcherSource, List[T_Dispatcher]]]:
        annotation, is_optional_param = self.preprocess_param_annotation(annotation)
        self.parameter_contexts.append(ParameterContext(
            name, annotation, default, [], optional=is_optional_param
        ))

        result = None
        try:
            start_offset = self._index + int(bool(self._index))
            for self.execution_contexts[-1]._index, (dispatcher, dispatcher_callable, source) in \
                enumerate(itertools.islice(self.dispatcher_generator(),
                    start_offset, None, None
            ), start=start_offset):
                result = await self.execute_dispatcher_callable(dispatcher_callable)
                
                if result is None:
                    continue
                
                if result.__class__ is Force:
                    result = result.target
                
                self.execution_contexts[-1]._index = 0
                return (
                    result, weakref.ref(dispatcher), source,
                    list(map(lambda x: weakref.ref(x), itertools.islice(
                        self.dispatcher_generator(), start_offset, self._index
                    )))
                ) if enable_extra_return else result
            else:
                if is_optional_param:
                    self.execution_contexts[-1]._index = 0
                    return
                raise RequirementCrashed("the dispatching requirement crashed: ", self.name, self.annotation, self.default)
        finally:
            for dispatcher, dispatcher_callable, source in self.dispatcher_generator(
                lambda x: [DispatcherSource(self.execution_contexts[-1].always_dispatchers)]
            ):
                await self.execute_dispatcher_callable(dispatcher_callable)

            self.parameter_contexts.pop()
    
    async def lookup_using_current(self) -> Any:
        _, is_optional_param = self.preprocess_param_annotation(self.annotation)

        result = None
        try:
            for self.execution_contexts[-1]._index, (dispatcher, dispatcher_callable, source) in \
                enumerate(itertools.islice(self.dispatcher_generator(),
                    self._index + int(bool(self._index)), None, None
            ), start=self._index + int(bool(self._index))):
                result = await self.execute_dispatcher_callable(dispatcher_callable)
                
                if result is None:
                    continue
                
                if result.__class__ is Force:
                    result = result.target
                
                self.execution_contexts[-1]._index = 0
                return result
            else:
                if is_optional_param:
                    self.execution_contexts[-1]._index = 0
                    return
                raise RequirementCrashed("the dispatching requirement crashed: ", self.name, self.annotation, self.default)
        finally:
            for dispatcher, dispatcher_callable, source in self.dispatcher_generator(
                lambda x: [DispatcherSource(self.execution_contexts[-1].always_dispatchers)]
            ):
                await self.execute_dispatcher_callable(dispatcher_callable)

    async def lookup_by(self, dispatcher: T_Dispatcher,
        name: str, annotation: Any, default: Any,
        enable_extra_return: bool = False
    ) -> Union[Any, Tuple[Any, T_Dispatcher, DispatcherSource, List[T_Dispatcher]]]:
        annotation, is_optional_param = self.preprocess_param_annotation(annotation)
        self.parameter_contexts.append(ParameterContext(
            name, annotation, default, [], optional=is_optional_param
        ))

        result = None
        try:
            start_offset = self._index + int(bool(self._index))
            for self.execution_contexts[-1]._index, (dispatcher, dispatcher_callable, source) in \
                enumerate(itertools.islice(self.dispatcher_generator(lambda x: [DispatcherSource([dispatcher])]),
                    start_offset, None, None
            ), start=start_offset):
                result = await self.execute_dispatcher_callable(dispatcher_callable)
                
                if result is None:
                    continue
                
                if result.__class__ is Force:
                    result = result.target
                
                self.execution_contexts[-1]._index = 0
                return (
                    result, weakref.ref(dispatcher), source,
                    list(map(lambda x: weakref.ref(x), itertools.islice(
                        self.dispatcher_generator(), start_offset, self._index
                    )))
                ) if enable_extra_return else result
            else:
                if is_optional_param:
                    self.execution_contexts[-1]._index = 0
                    return
                raise RequirementCrashed("the dispatching requirement crashed: ", self.name, self.annotation, self.default)
        finally:
            for dispatcher, dispatcher_callable, source in self.dispatcher_generator(
                lambda x: [DispatcherSource(self.execution_contexts[-1].always_dispatchers)]
            ):
                await self.execute_dispatcher_callable(dispatcher_callable)

            self.parameter_contexts.pop()

    async def lookup_by_directly(self, dispatcher: T_Dispatcher, name: str, annotation: Any, default: Any) -> Any:
        annotation, is_optional_param = self.preprocess_param_annotation(annotation)
        self.parameter_contexts.append(ParameterContext(
            name, annotation, default, [], optional=is_optional_param
        ))

        if dispatcher.__class__ is type and issubclass(dispatcher, BaseDispatcher):
            dispatcher_callable = dispatcher().catch
        elif hasattr(dispatcher, "catch"):
            dispatcher_callable = dispatcher.catch
        elif callable(dispatcher):
            dispatcher_callable = dispatcher
        else:
            raise ValueError("invaild dispatcher: ", dispatcher)
    
        try:
            result = await self.execute_dispatcher_callable(dispatcher_callable)
            if result.__class__ is Force:
                return result.target

            return result
        finally:
            self.parameter_contexts.pop()