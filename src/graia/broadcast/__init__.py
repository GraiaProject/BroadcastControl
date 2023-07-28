import asyncio
import inspect
import pprint
import sys
import traceback
from contextlib import asynccontextmanager
from typing import Callable, Dict, Iterable, List, Optional, Set, Type, Union

from .builtin.derive import DeriveDispatcher
from .builtin.event import EventExceptionThrown
from .entities.decorator import Decorator
from .entities.dispatcher import BaseDispatcher
from .entities.event import Dispatchable
from .entities.exectarget import ExecTarget
from .entities.listener import Listener
from .entities.namespace import Namespace
from .entities.signatures import Force, RemoveMe
from .exceptions import (
    DisabledNamespace,
    ExecutionStop,
    ExistedNamespace,
    InvalidEventName,
    PropagationCancelled,
    RegisteredEventListener,
    RequirementCrashed,
    UnexistedNamespace,
)
from .interfaces.decorator import DecoratorInterface
from .interfaces.dispatcher import DispatcherInterface
from .typing import T_Dispatcher
from .utilles import (
    CoverDispatcher,
    Ctx,
    argument_signature,
    dispatcher_mixin_handler,
    group_dict,
    run_always_await,
)


class Broadcast:
    loop: asyncio.AbstractEventLoop

    default_namespace: Namespace
    namespaces: List[Namespace]
    listeners: List[Listener]

    decorator_interface: DecoratorInterface

    event_ctx: Ctx[Dispatchable]

    debug_flag: bool

    prelude_dispatchers: List["T_Dispatcher"]
    finale_dispatchers: List["T_Dispatcher"]

    _background_tasks: Set[asyncio.Task] = set()

    def __init__(
        self,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        debug_flag: bool = False,
    ):
        self.loop = loop or asyncio.new_event_loop()
        self.default_namespace = Namespace(name="default", default=True)
        self.debug_flag = debug_flag
        self.namespaces = []
        self.listeners = []
        self.event_ctx = Ctx("bcc_event_ctx")
        self.decorator_interface = DecoratorInterface()
        self.prelude_dispatchers = [self.decorator_interface, DeriveDispatcher()]
        self.finale_dispatchers = []

        @self.prelude_dispatchers.append
        class BroadcastBuiltinDispatcher(BaseDispatcher):
            @staticmethod
            async def catch(interface: DispatcherInterface):
                if interface.annotation is interface.event.__class__:
                    return interface.event
                elif interface.annotation is Broadcast:
                    return interface.broadcast
                elif interface.annotation is DispatcherInterface:
                    return interface

    def default_listener_generator(self, event_class) -> Iterable[Listener]:
        return list(
            filter(
                lambda x: all(
                    [
                        not x.namespace.hide,
                        not x.namespace.disabled,
                        event_class in x.listening_events,
                    ]
                ),
                self.listeners,
            )
        )

    async def layered_scheduler(
        self,
        listener_generator: Iterable[Listener],
        event: Dispatchable,
        addition_dispatchers: Optional[List["T_Dispatcher"]] = None,
    ):
        grouped: Dict[int, List[Listener]] = group_dict(
            listener_generator, lambda x: x.priorities.get(event.__class__) or x.priority
        )
        event_dispatcher_mixin = dispatcher_mixin_handler(event.Dispatcher)
        if addition_dispatchers:
            event_dispatcher_mixin = event_dispatcher_mixin + addition_dispatchers
        with self.event_ctx.use(event):
            for _, current_group in sorted(grouped.items(), key=lambda x: x[0]):
                tasks = [
                    asyncio.create_task(self.Executor(target=i, dispatchers=event_dispatcher_mixin))
                    for i in current_group
                ]
                done_tasks, _ = await asyncio.wait(tasks)
                for task in done_tasks:
                    if task.exception().__class__ is PropagationCancelled:
                        return

    async def Executor(
        self,
        target: Union[Callable, ExecTarget],
        dispatchers: Optional[List[T_Dispatcher]] = None,
        post_exception_event: bool = True,
        print_exception: bool = True,
        use_global_dispatchers: bool = True,
        depth: int = 0,
    ):
        is_exectarget = is_listener = False
        current_oplog = None
        if isinstance(target, Listener):
            is_exectarget = is_listener = True
            current_oplog = target.oplog.setdefault(self.event_ctx.get().__class__, {})
            # if it's a listener, the event should be set.
        elif isinstance(target, ExecTarget):
            is_exectarget = True
            current_oplog = target.oplog.setdefault(..., {})
            # also, Ellipsis is good.

        if is_listener and target.namespace.disabled:  # type: ignore
            raise DisabledNamespace("caught a disabled namespace: {0}".format(target.namespace.name))  # type: ignore

        target_callable: Callable = target.callable if is_exectarget else target  # type: ignore
        parameter_compile_result = {}

        dispatchers: List[T_Dispatcher] = [
            *(self.prelude_dispatchers if use_global_dispatchers else []),
            *(dispatchers if dispatchers else []),
            *(target.dispatchers if is_exectarget else []),
            *(target.namespace.injected_dispatchers if is_listener else []),  # type: ignore
            *(self.finale_dispatchers if use_global_dispatchers else []),
        ]

        dii = DispatcherInterface(self, dispatchers, depth)
        dii_token = dii.ctx.set(dii)
        try:
            for dispatcher in dispatchers:
                i = getattr(dispatcher, "beforeExecution", None)
                if i:
                    await run_always_await(i, dii)  # type: ignore

            if is_exectarget:
                for name, annotation, default in argument_signature(target_callable):
                    origin = current_oplog.get(name)  # type: ignore
                    dii.current_oplog = origin.copy() if origin else []
                    parameter_compile_result[name] = await dii.lookup_param(name, annotation, default)
                    if name not in dii.success:
                        current_oplog[name] = dii.current_oplog  # type: ignore

                dii.current_oplog = []
                for hl_d in target.decorators:
                    await dii.lookup_by_directly(
                        self.decorator_interface,
                        "_bcc_headless_decorators",
                        None,
                        hl_d,
                    )

            else:
                for name, annotation, default in argument_signature(target_callable):
                    parameter_compile_result[name] = await dii.lookup_param(name, annotation, default)

            for dispatcher in dispatchers:
                i = getattr(dispatcher, "afterDispatch", None)
                if i:
                    await run_always_await(i, dii, None, None)

            dii.exec_result.set_result(await run_always_await(target_callable, **parameter_compile_result))
        except (ExecutionStop, PropagationCancelled):
            raise
        except RequirementCrashed as e:
            if depth != 0:
                if not hasattr(e, "__target__"):
                    e.__target__ = target_callable
                raise e
            name, *_ = e.args
            param = inspect.signature(getattr(e, "__target__", target_callable)).parameters[name]
            code = target_callable.__code__
            etype: Type[Exception] = type(
                "RequirementCrashed",
                (RequirementCrashed, SyntaxError),
                {},
            )
            _args = (code.co_filename, code.co_firstlineno, 1, str(param))
            if sys.version_info >= (3, 10):
                _args += (code.co_firstlineno, len(name) + 1)
            traceback.print_exception(
                etype,
                etype(
                    f"Unable to lookup parameter ({param}) by dispatchers\n{pprint.pformat(dispatchers)}",
                    _args,
                ),
                e.__traceback__,
            )
            raise
        except Exception as e:
            if depth != 0:
                raise
            event: Optional[Dispatchable] = self.event_ctx.get()
            if event is not None and event.__class__ is not EventExceptionThrown:
                if print_exception:
                    traceback.print_exc()
                if post_exception_event:
                    self.postEvent(EventExceptionThrown(exception=e, event=event))
            raise
        finally:
            _, exception, tb = sys.exc_info()
            for dispatcher in dispatchers:
                i = getattr(dispatcher, "afterExecution", None)
                if i:
                    await run_always_await(i, dii, exception, tb)  # type: ignore

            dii.ctx.reset(dii_token)

        result = dii.exec_result.result()
        if result.__class__ is Force:
            return result.target
        elif result is RemoveMe:
            if is_listener and target in self.listeners:
                self.listeners.remove(target)
        return result

    @asynccontextmanager
    async def param_compile(
        self,
        dispatchers: Optional[List[T_Dispatcher]] = None,
        post_exception_event: bool = True,
        print_exception: bool = True,
        use_global_dispatchers: bool = True,
    ):
        dispatchers: List[T_Dispatcher] = [
            *(self.prelude_dispatchers if use_global_dispatchers else []),
            *(dispatchers if dispatchers else []),
            *(self.finale_dispatchers if use_global_dispatchers else []),
        ]

        dii = DispatcherInterface(self, dispatchers, 0)
        dii_token = dii.ctx.set(dii)

        try:
            for dispatcher in dispatchers:
                i = getattr(dispatcher, "beforeExecution", None)
                if i:
                    await run_always_await(i, dii)  # type: ignore
            yield dii
        except RequirementCrashed:
            traceback.print_exc()
            raise
        except Exception as e:
            event: Optional[Dispatchable] = self.event_ctx.get()
            if event is not None and event.__class__ is not EventExceptionThrown:
                if print_exception:
                    traceback.print_exc()
                if post_exception_event:
                    self.postEvent(EventExceptionThrown(exception=e, event=event))
            raise
        finally:
            _, exception, tb = sys.exc_info()
            for dispatcher in dispatchers:
                i = getattr(dispatcher, "afterExecution", None)
                if i:
                    await run_always_await(i, dii, exception, tb)  # type: ignore

            dii.ctx.reset(dii_token)

    def postEvent(self, event: Dispatchable, upper_event: Optional[Dispatchable] = None):
        task = self.loop.create_task(
            self.layered_scheduler(
                listener_generator=self.default_listener_generator(event.__class__),
                event=event,
                addition_dispatchers=[
                    CoverDispatcher(i, upper_event) for i in dispatcher_mixin_handler(upper_event.Dispatcher)
                ]
                if upper_event
                else [],
            )
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    @staticmethod
    def event_class_generator(target=Dispatchable):
        for i in target.__subclasses__():
            yield i
            if i.__subclasses__():
                yield from Broadcast.event_class_generator(i)

    @staticmethod
    def findEvent(name: str):
        for i in Broadcast.event_class_generator():
            if i.__name__ == name:
                return i

    def getDefaultNamespace(self):
        return self.default_namespace

    def createNamespace(self, name, *, priority: int = 0, hide: bool = False, disabled: bool = False):
        if self.containNamespace(name):
            raise ExistedNamespace(name, "has been created!")
        self.namespaces.append(Namespace(name=name, priority=priority, hide=hide, disabled=disabled))
        return self.namespaces[-1]

    def removeNamespace(self, name):
        if not self.containNamespace(name):
            raise UnexistedNamespace(name)
        for index, i in enumerate(self.namespaces):
            if i.name == name:
                self.namespaces.pop(index)
                return

    def containNamespace(self, name):
        return any(i.name == name for i in self.namespaces)

    def getNamespace(self, name) -> "Namespace":
        if self.containNamespace(name):
            for i in self.namespaces:
                if i.name == name:
                    return i
        raise UnexistedNamespace(name)

    def hideNamespace(self, name):
        ns = self.getNamespace(name)
        ns.hide = True

    def unhideNamespace(self, name):
        ns = self.getNamespace(name)
        ns.hide = False

    def disableNamespace(self, name):
        ns = self.getNamespace(name)
        ns.disabled = True

    def enableNamespace(self, name):
        ns = self.getNamespace(name)
        ns.disabled = False

    def containListener(self, target):
        return any(i.callable == target for i in self.listeners)

    def getListener(self, target):
        for i in self.listeners:
            if i.callable == target:
                return i

    def removeListener(self, target):
        self.listeners.remove(target)

    def receiver(
        self,
        event: Union[str, Type[Dispatchable]],
        priority: int = 16,
        dispatchers: Optional[List[T_Dispatcher]] = None,
        namespace: Optional[Namespace] = None,
        decorators: Optional[List[Decorator]] = None,
    ):
        if isinstance(event, str):
            _name = event
            event = self.findEvent(event)  # type: ignore
            if not event:
                raise InvalidEventName(f"{_name} is not valid!")
        priority = int(priority)

        def receiver_wrapper(callable_target):
            listener = self.getListener(callable_target)
            if not listener:
                self.listeners.append(
                    Listener(
                        callable=callable_target,
                        namespace=namespace or self.getDefaultNamespace(),
                        inline_dispatchers=dispatchers or [],
                        priority=priority,
                        listening_events=[event],  # type: ignore
                        decorators=decorators or [],
                    )
                )
            elif event in listener.listening_events:
                raise RegisteredEventListener(event.__name__, "has been registered!")  # type: ignore
            else:
                listener.listening_events.append(event)  # type: ignore
            return callable_target

        return receiver_wrapper
