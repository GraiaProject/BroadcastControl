from __future__ import annotations

from typing import Protocol, TypeVar

from ..entities.dispatcher import BaseDispatcher
from ..entities.signatures import ObjectContainer
from ..interfaces.dispatcher import DispatcherInterface

try:
    from typing_extensions import get_args
except ImportError:
    from typing import get_args


T = TypeVar("T")


class Derive(Protocol[T]):
    async def __call__(self, value: T, dispatcher_interface: DispatcherInterface) -> T:
        ...


class Origin(ObjectContainer):
    """直接为 Derive 指定 Origin Type, 覆盖原本从形参中获取的 Origin Type."""


class DeriveDispatcher(BaseDispatcher):
    async def catch(self, interface: DispatcherInterface):
        if not interface.is_annotated:
            return
        args = get_args(interface.annotation)
        origin_arg, meta = args[0], args[1:]
        if meta and isinstance(meta[0], Origin):
            origin_arg = meta[0].target
            meta = meta[1:]
        result = await interface.lookup_param(interface.name, origin_arg, interface.default)
        for i in meta:
            result = await i(result, interface)
        return result
