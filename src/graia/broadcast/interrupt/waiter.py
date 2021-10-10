from abc import ABCMeta, abstractmethod
from typing import Any, List, Type

from ..entities.decorator import Decorator
from ..entities.event import Dispatchable
from ..typing import T_Dispatcher


class Waiter(metaclass=ABCMeta):
    listening_events: List[Type[Dispatchable]]
    using_dispatchers: List[T_Dispatcher]
    using_decorators: List[Decorator]
    priority: int
    block_propagation: bool

    @classmethod
    def create(
        cls,
        listening_events: List[Type[Dispatchable]],
        using_dispatchers: List[T_Dispatcher] = None,
        using_decorators: List[Decorator] = None,
        priority: int = 15,  # 默认情况下都是需要高于默认 16 的监听吧...
        block_propagation: bool = False,
    ) -> Type["Waiter"]:
        async def detected_event(self) -> Any:
            pass

        return type(  # type: ignore
            "AbstractWaiter",
            (cls,),
            {
                "listening_events": listening_events,
                "using_dispatchers": using_dispatchers,
                "using_decorators": using_decorators,
                "priority": priority,
                "block_propagation": block_propagation,
                "detected_event": abstractmethod(detected_event),
            },
        )

    async def detected_event(self) -> Any:
        pass

    @classmethod
    def create_using_function(
        cls,
        listening_events: List[Type[Dispatchable]],
        using_dispatchers: List[T_Dispatcher] = None,
        using_decorators: List[Decorator] = None,
        priority: int = 15,  # 默认情况下都是需要高于默认 16 的监听吧...
        block_propagation: bool = False,
    ):
        def wrapper(func):
            return type(
                "SingleWaiter",
                (
                    cls.create(
                        listening_events,
                        using_dispatchers,
                        using_decorators,
                        priority,
                        block_propagation,
                    ),
                ),
                {"detected_event": staticmethod(func)},
            )()

        return wrapper
