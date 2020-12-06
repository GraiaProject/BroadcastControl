from typing import Any, Optional, Type, Union
from graia.broadcast import Broadcast
from graia.broadcast.entities.exectarget import ExecTarget
from graia.broadcast.priority import Priority
from graia.broadcast.entities.event import BaseEvent
from abc import ABCMeta, abstractmethod
from graia.broadcast.utilles import run_always_await
from graia.broadcast.entities.signatures import Force, RemoveMe
from graia.broadcast.exceptions import PropagationCancelled
import asyncio
from .waiter import Waiter


class ActiveStats:
    def __init__(self) -> None:
        self.actived = False

    def get(self) -> bool:
        return self.actived

    def set(self) -> bool:
        self.actived = True
        return True


class Value:
    value: Any

    def __init__(self) -> None:
        self.value = None

    def getValue(self) -> Any:
        return self.value

    def setValue(self, value) -> None:
        self.value = value


class InterruptControl:
    """即中断控制, 主要是用于监听器/其他地方进行对符合特定要求的事件的捕获, 并返回事件.

    Methods:
        coroutine wait(interrupt: Interrupt) -> Any: 该方法主要用于在当前执行处堵塞当前协程,
            同时将一个一次性使用的监听器挂载, 只要获取到符合条件的事件, 该方法会通过你传入的 `Interrupt` 实例的方法 `trigger`,
            获取处理得到的值并返回; 无论如何, 用于一次性监听使用的监听器总会被销毁.
    """

    broadcast: Broadcast

    def __init__(self, broadcast: Broadcast) -> None:
        self.broadcast = broadcast

    async def wait(
        self, waiter: Waiter, priority: Optional[Union[int, Priority]] = None, **kwargs
    ):
        """生成一一次性使用的监听器并将其挂载, 该监听器用于获取特定类型的事件, 并根据设定对事件进行过滤;
        当获取到符合条件的对象时, 堵塞将被解除, 同时该方法返回从监听器得到的值.

        Args:
            waiter (Waiter): 等待器
            priority (Union[int, Priority]): 中断 inline 监听器的优先级, Defaults to 15.
            **kwargs: 都会直接传入 Broadcast.receiver.

        Returns:
            Any: 通常这个值由中断本身定义并返回.
        """
        local_event = asyncio.Event()
        value_container = Value()
        active_stat = ActiveStats()

        listener_callables = []
        for event_type in waiter.listening_events:
            listener_callable = self.leader_listener_generator(
                local_event, waiter, event_type, value_container, active_stat
            )
            self.broadcast.receiver(
                event_type, priority=priority or waiter.priority, **kwargs
            )(listener_callable)
            listener_callables.append(listener_callable)

        try:
            await local_event.wait()
        finally:  # 删除 Listener
            if not local_event.is_set() or not active_stat.get():
                for i in listener_callables:
                    self.broadcast.removeListener(self.broadcast.getListener(i))
        return value_container.getValue()

    def leader_listener_generator(
        self,
        event_lock: asyncio.Event,
        waiter: Waiter,
        event_type: Type[BaseEvent],
        value_container: Value,
        active_stat: ActiveStats,
    ):
        async def inside_listener(event: event_type):
            if active_stat.get():
                return RemoveMe()

            result = await self.broadcast.Executor(
                target=ExecTarget(
                    callable=waiter.detected_event,
                    inline_dispatchers=waiter.using_dispatchers,
                    headless_decoraters=waiter.using_decorators,
                    enable_internal_access=waiter.enable_internal_access,
                ),
                event=event,
            )

            if result is not None:
                active_stat.set()
                event_lock.set()
                value_container.setValue(result)
                if not waiter.block_propagation:
                    return RemoveMe()
                raise PropagationCancelled()

        return inside_listener
