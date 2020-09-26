from typing import Any, Callable, List, Type, Union

from pydantic.dataclasses import dataclass

from ..entities.dispatcher import BaseDispatcher
from ..entities.event import BaseEvent
from ..entities.listener import Listener


class ExecutorProtocol:
    def __init__(self,
        target: Union[Callable, Listener],
        event: BaseEvent,
        dispatchers: List[Union[
            Type[BaseDispatcher],
            Callable,
            BaseDispatcher,
        ]] = None,
        hasReferrer: bool = False,
        enableInternalAccess: bool = False,
    ) -> None:
        self.target = target
        self.dispatchers = dispatchers or []
        self.event = event
        self.hasReferrer = hasReferrer
        self.enableInternalAccess = enableInternalAccess

    target: Union[Callable, Listener]
    event: BaseEvent
    dispatchers: List[Union[
        Type[BaseDispatcher],
        Callable,
        BaseDispatcher
    ]]
    hasReferrer: bool = False
    enableInternalAccess: bool = False
