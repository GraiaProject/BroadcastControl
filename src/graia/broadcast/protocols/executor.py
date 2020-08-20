from typing import Any, Callable, List, Type, Union

from pydantic import BaseModel  # pylint: disable=no-name-in-module

from ..entities.dispatcher import BaseDispatcher
from ..entities.event import BaseEvent
from ..entities.listener import Listener


class ExecutorProtocol(BaseModel):
    target: Union[Callable, Listener]
    dispatchers: List[Union[
        Type[BaseDispatcher],
        Callable,
        BaseDispatcher
    ]] = []
    event: BaseEvent
    hasReferrer: bool = False
    enableInternalAccess: bool = False

    class Config:
        arbitrary_types_allowed = True
