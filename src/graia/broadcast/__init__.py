import asyncio
import sys
import traceback
from typing import (Callable, Dict, Generator, Iterable, List, Optional, Set,
                    Type, Union)

from graia.broadcast.entities.track_log import TrackLog, TrackLogType

from .builtin.event import ExceptionThrowed
from .entities.decorator import Decorator
from .entities.dispatcher import BaseDispatcher
from .entities.event import Dispatchable
from .entities.exectarget import ExecTarget
from .entities.listener import Listener
from .entities.namespace import Namespace
from .entities.signatures import Force, RemoveMe
from .exceptions import (DisabledNamespace, ExecutionStop, ExistedNamespace,
                         InvaildEventName, PropagationCancelled,
                         RegisteredEventListener, RequirementCrashed,
                         UnexistedNamespace)
from .interfaces.decorator import DecoratorInterface
from .interfaces.dispatcher import DispatcherInterface
from .typing import T_Dispatcher
from .utilles import (Ctx, argument_signature, cached_isinstance,
                      dispatcher_mixin_handler, group_dict, printer,
                      run_always_await_safely)


class Broadcast:
    loop: asyncio.AbstractEventLoop

    default_namespace: Namespace
    namespaces: List[Namespace]
    listeners: List[Listener]

    dispatcher_interface: DispatcherInterface
    decorator_interface: DecoratorInterface

    event_ctx: Ctx[Dispatchable]

    debug_flag: bool

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
        self.dispatcher_interface = DispatcherInterface(self)
        self.decorator_interface = DecoratorInterface(self.dispatcher_interface)
        self.dispatcher_interface.execution_contexts[0].dispatchers.insert(
            0, self.decorator_interface
        )

        @self.dispatcher_interface.inject_global_raw
        async def _(interface: DispatcherInterface):
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
        self, listener_generator: Iterable[Listener], event: Dispatchable
    ):
        grouped: Dict[int, List[Listener]] = group_dict(
            listener_generator, lambda x: x.priority
        )
        event_dispatcher_mixin = dispatcher_mixin_handler(event.Dispatcher)
        with self.event_ctx.use(event):
            for _, current_group in sorted(grouped.items(), key=lambda x: x[0]):
                coros = [
                    self.Executor(target=i, dispatchers=event_dispatcher_mixin)  # type: ignore
                    for i in current_group
                ]
                done_tasks, _ = await asyncio.wait(coros)
                for task in done_tasks:
                    if task.exception().__class__ is PropagationCancelled:
                        break

    async def Executor(
        self,
        target: Union[Callable, ExecTarget],
        dispatchers: List[T_Dispatcher] = None,
        post_exception_event: bool = True,
        print_exception: bool = True,
    ):
        is_exectarget = cached_isinstance(target, ExecTarget)
        is_listener = cached_isinstance(target, Listener)
        event: Optional[Dispatchable] = self.event_ctx.get(None)

        if is_listener:
            if target.namespace.disabled:  # type: ignore
                raise DisabledNamespace(
                    "catched a disabled namespace: {0}".format(target.namespace.name)  # type: ignore
                )

        target_callable = target.callable if is_exectarget else target
        parameter_compile_result = {}

        track_logs: TrackLog = TrackLog()
        async with self.dispatcher_interface.start_execution(
            [
                *(dispatchers or []),
                *(target.namespace.injected_dispatchers if is_listener else []),  # type: ignore
                *(target.inline_dispatchers if is_exectarget else []),
            ],
            track_logs,
        ) as dii:
            await dii.exec_lifecycle("beforeExecution")
            try:
                await dii.exec_lifecycle("beforeDispatch")

                if is_exectarget:
                    if target.maybe_failure:
                        initial_path = dii.init_dispatch_path()
                        for name, annotation, default in argument_signature(
                            target_callable
                        ):
                            if (
                                target.param_paths.setdefault(name, initial_path)
                                is initial_path
                            ):
                                target.param_paths[name + "$set"] = set()
                            parameter_compile_result[name] = await dii.lookup_param(
                                name, annotation, default, target.param_paths[name]  # type: ignore
                            )
                    else:
                        for name, annotation, default in argument_signature(
                            target_callable
                        ):
                            parameter_compile_result[
                                name
                            ] = await dii.lookup_param_without_log(
                                name, annotation, default, target.param_paths[name]  # type: ignore
                            )

                    for hl_d in target.decorators:
                        await dii.lookup_by_directly(
                            self.decorator_interface,
                            "_bcc_headless_decorators",
                            None,
                            hl_d,
                        )

                else:
                    for name, annotation, default in argument_signature(
                        target_callable
                    ):
                        parameter_compile_result[
                            name
                        ] = await dii.lookup_param_without_log(
                            name, annotation, default, target.param_paths[name]  # type: ignore
                        )

                result = await run_always_await_safely(
                    target_callable, **parameter_compile_result
                )
            except (ExecutionStop, PropagationCancelled):
                raise
            except RequirementCrashed:
                traceback.print_exc()
                raise
            except Exception as e:
                if event is not None:
                    if print_exception or event.__class__ is ExceptionThrowed:
                        traceback.print_exc()
                    if post_exception_event and event.__class__ is not ExceptionThrowed:
                        self.postEvent(ExceptionThrowed(exception=e, event=event))
                raise
            finally:
                _, exception, tb = sys.exc_info()
                await dii.exec_lifecycle("afterDispatch", exception, tb)
                await dii.exec_lifecycle("afterTargetExec", exception, tb)
                await dii.exec_lifecycle("afterExecution", exception, tb)

                if is_exectarget and not track_logs.fluent_success:
                    current_paths = target.param_paths
                    current_path: Optional[List[List["T_Dispatcher"]]] = None
                    current_path_set: Optional[Set["T_Dispatcher"]] = None
                    has_failures: set = set()

                    for log in track_logs.log:
                        if log[0] is TrackLogType.LookupStart:
                            current_path = current_paths[log[1]]  # type: ignore
                            current_path_set = current_paths[log[1] + "$set"]  # type: ignore
                        elif log[0] is TrackLogType.LookupEnd:
                            current_path = None
                        elif (
                            current_path is not None
                            and log[0] is TrackLogType.Result
                            and log[2] not in current_path_set  # type: ignore
                        ):
                            current_path[0].append(log[2])  # type: ignore
                            current_path_set.add(log[2])  # type: ignore
                        elif log[0] is TrackLogType.Continue:
                            has_failures.add(log[1])

                    target.maybe_failure.symmetric_difference_update(has_failures)

            if result.__class__ is Force:
                return result.content

            if result.__class__ is RemoveMe:
                if cached_isinstance(target, Listener):
                    if target in self.listeners:
                        self.listeners.pop(self.listeners.index(target))

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

    def createNamespace(
        self, name, *, priority: int = 0, hide: bool = False, disabled: bool = False
    ):
        if self.containNamespace(name):
            raise ExistedNamespace(name, "has been created!")
        self.namespaces.append(
            Namespace(name=name, priority=priority, hide=hide, disabled=disabled)
        )
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
        dispatchers: List[Type[BaseDispatcher]] = [],
        namespace: Namespace = None,
        decorators: List[Decorator] = [],
    ):
        if cached_isinstance(event, str):
            _name = event
            event = self.findEvent(event)  # type: ignore
            if not event:
                raise InvaildEventName(_name + " is not vaild!")  # type: ignore
        priority = (type(priority) == int) and priority or int(priority)  # 类型转换

        def receiver_wrapper(callable_target):
            may_listener = self.getListener(callable_target)
            if not may_listener:
                self.listeners.append(
                    Listener(
                        callable=callable_target,
                        namespace=namespace or self.getDefaultNamespace(),
                        inline_dispatchers=dispatchers,  # type: ignore
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
