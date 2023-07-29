import typing
from typing import Any, Optional, Union

from ..entities.decorator import Decorator
from ..entities.signatures import Force
from ..exceptions import RequirementCrashed
from ..interfaces.decorator import DecoratorInterface
from .depend import Depend as Depend


class OptionalParam(Decorator):
    pre = True

    def __init__(self, origin: Any):
        self.origin = origin

    async def target(self, interface: DecoratorInterface) -> Optional[Any]:
        annotation = interface.annotation
        if typing.get_origin(annotation) is Union:
            annotation = Union[tuple(x for x in typing.get_args(annotation) if x not in (None, type(None)))]  # type: ignore
        try:
            return Force(
                await interface.dispatcher_interface.lookup_by_directly(
                    interface,
                    interface.dispatcher_interface.name,
                    annotation,
                    self.origin,
                )
            )
        except RequirementCrashed:
            return Force()
