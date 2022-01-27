from typing import TYPE_CHECKING, Type, Union

if TYPE_CHECKING:
    from graia.broadcast.entities.dispatcher import BaseDispatcher

T_Dispatcher = Union[Type["BaseDispatcher"], "BaseDispatcher"]
