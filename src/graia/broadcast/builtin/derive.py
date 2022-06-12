from __future__ import annotations

from typing import Protocol, TypeVar

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

try:
    from typing_extensions import get_args
except ImportError:
    from typing import get_args


T = TypeVar("T")


class Derive(Protocol[T]):
    async def __call__(self, value: T, dispatcher_interface: DispatcherInterface) -> T:
        ...


class DeriveDispatcher(BaseDispatcher):
    async def catch(self, interface: DispatcherInterface):
        if not interface.is_annotated:
            return
        args = get_args(interface.annotation)
        origin_arg, meta = args[0], args[1:]
        result = await interface.lookup_param(interface.name, origin_arg, interface.default)
        for i in meta:
            result = await i(result, interface)
        return result
