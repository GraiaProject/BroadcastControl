from pydantic import BaseModel # pylint: disable=no-name-in-module
from typing import Callable, Any, List, Union
from ..entities.dispatcher import BaseDispatcher
from ..entities.listener import Listener
from ..entities.event import BaseEvent

class ExecutorProtocol(BaseModel):
    target: Union[Callable, Listener]
    dispatchers: List[BaseDispatcher] = []
    event: BaseEvent
    hasReferrer: bool = False

    class Config:
        arbitrary_types_allowed = True