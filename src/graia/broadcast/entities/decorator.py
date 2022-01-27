from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from graia.broadcast.interfaces.decorator import DecoratorInterface


class Decorator:
    target: Callable[["DecoratorInterface"], Any]
    pre: bool = False
