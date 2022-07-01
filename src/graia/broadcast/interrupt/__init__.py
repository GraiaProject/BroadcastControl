import asyncio
from asyncio import Future, get_running_loop
from typing import Optional, Type, Union

from .. import Broadcast
from ..entities.event import Dispatchable
from ..entities.exectarget import ExecTarget
from ..entities.signatures import RemoveMe
from ..exceptions import PropagationCancelled
from ..priority import Priority
from ..utilles import dispatcher_mixin_handler
from .waiter import Waiter


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
        self, waiter: Waiter, priority: Optional[Union[int, Priority]] = None, timeout: Optional[float] = None, **kwargs
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
        future = get_running_loop().create_future()

        listeners = set()
        for event_type in waiter.listening_events:
            listener_callable = self.leader_listener_generator(waiter, event_type, future)
            self.broadcast.receiver(event_type, priority=priority or waiter.priority, **kwargs)(listener_callable)
            listener = self.broadcast.getListener(listener_callable)
            listeners.add(listener)

        try:
            return await asyncio.wait_for(future, timeout) if timeout else await future
        finally:  # 删除 Listener
            if not future.done():
                for i in listeners:
                    self.broadcast.removeListener(i)

    def leader_listener_generator(self, waiter: Waiter, event_type: Type[Dispatchable], future: Future):
        async def inside_listener(event: event_type):
            if future.done():
                return RemoveMe

            result = await self.broadcast.Executor(
                target=ExecTarget(
                    callable=waiter.detected_event,
                    inline_dispatchers=waiter.using_dispatchers,
                    decorators=waiter.using_decorators,
                ),
                dispatchers=dispatcher_mixin_handler(event.Dispatcher),
            )
            # at present, the state of `future` is absolutely unknown.
            if result is not None and not future.done():
                future.set_result(result)
                if not waiter.block_propagation:
                    return RemoveMe
                raise PropagationCancelled()

        return inside_listener
