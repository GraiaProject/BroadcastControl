from __future__ import annotations

import asyncio
from types import TracebackType
from typing import Awaitable, Callable

from ..entities.dispatcher import BaseDispatcher
from ..interfaces.dispatcher import DispatcherInterface


class DeferDispatcher(BaseDispatcher):
    async def beforeExecution(self, interface: DispatcherInterface):
        interface.local_storage["defer_callbacks"] = []

    async def catch(self, interface: DispatcherInterface):
        return

    async def afterExecution(
        self,
        interface: DispatcherInterface,
        exception: Exception | None,
        tb: TracebackType | None,
    ):
        callbacks: list[Callable[[DispatcherInterface, Exception | None, TracebackType | None], Awaitable[None]]]
        callbacks = interface.local_storage.get("defer_callbacks")  # type: ignore

        if not callbacks:
            return

        await asyncio.wait([i(interface, exception, tb) for i in callbacks])
