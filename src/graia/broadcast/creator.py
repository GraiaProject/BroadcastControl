from __future__ import annotations

from typing import TYPE_CHECKING

from creart import AbstractCreator, CreateTargetInfo, it

if TYPE_CHECKING:
    from . import Broadcast
    from .interrupt import InterruptControl


class BroadcastCreator(AbstractCreator):
    targets = (
        CreateTargetInfo(
            module="graia.broadcast",
            identify="Broadcast",
            humanized_name="Broadcast Control",
            description="<common,graia,broadcast> a high performance, highly customizable, elegantly designed event system based on asyncio",
            author=["GraiaProject@github"],
        ),
        CreateTargetInfo(
            module="graia.broadcast.interrupt",
            identify="InterruptControl",
            humanized_name="Interrupt",
            description="<common,graia,broadcast,interrupt> Interrupt feature for broadcast control.",
            author=["GraiaProject@github"],
        ),
    )

    @staticmethod
    def create(
        create_type: type[Broadcast | InterruptControl],
    ) -> Broadcast | InterruptControl:
        from . import Broadcast
        from .interrupt import InterruptControl

        if issubclass(create_type, Broadcast):
            return create_type()
        elif issubclass(create_type, InterruptControl):
            return create_type(it(Broadcast))
