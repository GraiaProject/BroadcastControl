import asyncio
import sys
import traceback
from collections import UserList
from typing import Callable, Dict, Iterable, List, Optional, Type, Union

from graia.broadcast.entities.dispatcher import BaseDispatcher

from .builtin.event import ExceptionThrowed
from .entities.decorator import Decorator
from .entities.event import Dispatchable
from .entities.exectarget import ExecTarget
from .entities.listener import Listener
from .entities.namespace import Namespace
from .entities.signatures import Force, RemoveMe
from .exceptions import (DisabledNamespace, ExecutionStop, ExistedNamespace,
                         InvalidEventName, PropagationCancelled,
                         RegisteredEventListener, RequirementCrashed,
                         UnexistedNamespace)
from .interfaces.decorator import DecoratorInterface
from .interfaces.dispatcher import DispatcherInterface
from .typing import T_Dispatcher
from .utilles import (Ctx, argument_signature, dispatcher_mixin_handler,
                      group_dict, run_always_await_safely)


class DebugList(UserList):
    def extend(self, item) -> None:
        print(item)
        return super().extend(item)

    def append(self, item) -> None:
        print(item)
        return super().append(item)

    def insert(self, i: int, item) -> None:
        print(i, item)
        return super().insert(i, item)


class Broadcast:
    loop: asyncio.AbstractEventLoop

    default_namespace: Namespace
    namespaces: List[Namespace]
    listeners: List[Listener]

    dispatcher_interface: DispatcherInterface
    decorator_interface: DecoratorInterface

    event_ctx: Ctx[Dispatchable]

    debug_flag: bool

    prelude_dispatchers: List["T_Dispatcher"]
    finale_dispatchers: List["T_Dispatcher"]

    def __init__(
        self,
        *,
        loop: asyncio.AbstractEventLoop = None,
        debug_flag: bool = False,
    ):
        self.loop = loop or asyncio.get_event_loop()
        self.default_namespace = Namespace(name="default", default=True)
        self.debug_flag = debug_flag
        self.namespaces = []
        self.listeners = []
        self.event_ctx = Ctx("bcc_event_ctx")
        self.decorator_interface = DecoratorInterface()
        self.prelude_dispatchers = [self.decorator_interface]
        self.finale_dispatchers = []

        @self.global_dispatchers.append
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

    async def layered_scheduler(self, listener_generator: Iterable[Listener], event: Dispatchable):
        grouped: Dict[int, List[Listener]] = group_dict(listener_generator, lambda x: x.priority)
        event_dispatcher_mixin = dispatcher_mixin_handler(event.Dispatcher)
        with self.event_ctx.use(event):
            for _, current_group in sorted(grouped.items(), key=lambda x: x[0]):
                coros = [self.Executor(target=i, dispatchers=event_dispatcher_mixin) for i in current_group]
                done_tasks, _ = await asyncio.wait(coros)
                for task in done_tasks:
                    if task.exception().__class__ is PropagationCancelled:
                        return

    async def Executor(
        self,
        target: Union[Callable, ExecTarget],
        dispatchers: List[T_Dispatcher] = None,
        post_exception_event: bool = True,
        print_exception: bool = True,
        use_global_dispatchers: bool = True,
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

        if is_listener:
            if target.namespace.disabled:  # type: ignore
                raise DisabledNamespace(
                    "caught a disabled namespace: {0}".format(target.namespace.name)  # type: ignore
                )

        target_callable = target.callable if is_exectarget else target  # type: ignore
        parameter_compile_result = {}

        dispatchers = [  # type: ignore
            *(self.prelude_dispatchers if use_global_dispatchers else []),
            *(dispatchers if dispatchers else []),
            *(target.dispatchers if is_exectarget else []),
            *(target.namespace.injected_dispatchers if is_listener else []),
            *(self.finale_dispatchers if use_global_dispatchers else []),
        ]

        dii = DispatcherInterface(self, dispatchers)
        dii_token = dii.ctx.set(dii)

        try:
            for dispatcher in dispatchers:
                i = getattr(dispatcher, "beforeExecution", None)
                if i:
                    await run_always_await_safely(i, dii)  # type: ignore

            if is_exectarget:
                for name, annotation, default in argument_signature(target_callable):  # type: ignore
                    dii.current_oplog = current_oplog.setdefault(name, [])
                    parameter_compile_result[name] = await dii.lookup_param(name, annotation, default)

                dii.current_oplog = []
                for hl_d in target.decorators:
                    await dii.lookup_by_directly(
                        self.decorator_interface,
                        "_bcc_headless_decorators",
                        None,
                        hl_d,
                    )

            else:
                for name, annotation, default in argument_signature(target_callable):  # type: ignore
                    parameter_compile_result[name] = await dii.lookup_param(name, annotation, default, [])

            for dispatcher in dispatchers:
                i = getattr(dispatcher, "afterDispatch", None)
                if i:
                    await run_always_await_safely(i, dii, None, None)  # type: ignore

            result = await run_always_await_safely(target_callable, **parameter_compile_result)
        except (ExecutionStop, PropagationCancelled):
            raise
        except RequirementCrashed:
            traceback.print_exc()
            raise
        except Exception as e:
            event: Optional[Dispatchable] = self.event_ctx.get()
            if event is not None and event.__class__ is not ExceptionThrowed:
                if print_exception:
                    traceback.print_exc()
                if post_exception_event:
                    self.postEvent(ExceptionThrowed(exception=e, event=event))
            raise
        finally:
            _, exception, tb = sys.exc_info()
            for dispatcher in dispatchers:
                i = getattr(dispatcher, "afterExecution", None)
                if i:
                    await run_always_await_safely(i, dii, exception, tb)  # type: ignore

            dii.ctx.reset(dii_token)

        if result.__class__ is Force:
            return result.content
        elif result is RemoveMe:
            if is_listener and target in self.listeners:
                self.listeners.remove(target)
        return result

    def postEvent(self, event: Dispatchable):
        self.loop.create_task(
            self.layered_scheduler(
                listener_generator=self.default_listener_generator(event.__class__),
                event=event,
            )
        )

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
        if self.containNamespace(name):
            for index, i in enumerate(self.namespaces):
                if i.name == name:
                    self.namespaces.pop(index)
                    return
        else:
            raise UnexistedNamespace(name)

    def containNamespace(self, name):
        for i in self.namespaces:
            if i.name == name:
                return True
        return False

    def getNamespace(self, name) -> "Namespace":
        if self.containNamespace(name):
            for i in self.namespaces:
                if i.name == name:
                    return i
            else:
                raise UnexistedNamespace(name)
        else:
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
        for i in self.listeners:
            if i.callable == target:
                return True
        return False

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
        dispatchers: List[T_Dispatcher] = None,
        namespace: Namespace = None,
        decorators: List[Decorator] = None,
    ):
        if isinstance(event, str):
            _name = event
            event = self.findEvent(event)  # type: ignore
            if not event:
                raise InvalidEventName(_name + " is not valid!")  # type: ignore
        priority = int(priority)

        def receiver_wrapper(callable_target):
            may_listener = self.getListener(callable_target)
            if not may_listener:
                self.listeners.append(
                    Listener(
                        callable=callable_target,
                        namespace=namespace or self.getDefaultNamespace(),
                        inline_dispatchers=dispatchers,
                        priority=priority,
                        listening_events=[event],  # type: ignore
                        decorators=decorators,
                    )
                )
            else:
                if event not in may_listener.listening_events:
                    may_listener.listening_events.append(event)  # type: ignore
                else:
                    raise RegisteredEventListener(event.__name__, "has been registered!")  # type: ignore
            return callable_target

        return receiver_wrapper
