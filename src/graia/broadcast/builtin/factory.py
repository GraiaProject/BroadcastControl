import traceback
from types import TracebackType
from typing import (
    Any,
    Callable,
    Generator,
    NamedTuple,
    Optional,
    Tuple,
    TypeVar,
    Literal,
    Union,
)
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from enum import IntEnum, auto

from graia.broadcast.utilles import printer


class StatusCodeEnum(IntEnum):
    DISPATCHING = 1

    DISPATCH_COMPLETED = 2
    EXECUTION_COMPLETED = 3

    DISPATCH_EXCEPTION = 4
    EXECUTION_EXCEPTION = 5


class ResponseCodeEnum(IntEnum):
    VALUE = 1


class ExcInfo(NamedTuple):
    exception: Exception
    traceback: TracebackType


T_DispatcherContextManager = Generator[
    Union[None, Tuple[Literal[ResponseCodeEnum.VALUE], Any]],
    Union[None, Tuple[StatusCodeEnum, Union[ExcInfo]]],
    None,
]


class DispatcherContextManager(BaseDispatcher):
    generator_factory: Callable[[Any], T_DispatcherContextManager]
    generator: T_DispatcherContextManager

    def __init__(self, generator_factory: Callable, args=None, kwargs=None) -> None:
        self.generator_factory = generator_factory
        self.args = args or ()
        self.kwargs = kwargs or {}

    def beforeExecution(self, interface: "DispatcherInterface"):
        self.generator = self.generator_factory(*self.args, **self.kwargs)
        next(self.generator)
        self.generator.send(interface)

    def catch(self, interface: "DispatcherInterface"):
        status, value = self.generator.send((StatusCodeEnum.DISPATCHING, None))
        if status is ResponseCodeEnum.VALUE:
            return value

    def afterDispatch(
        self,
        interface: "DispatcherInterface",
        exception: Optional[Exception],
        tb: Optional[TracebackType],
    ):
        try:
            if not tb:
                self.generator.send((StatusCodeEnum.DISPATCH_COMPLETED, None))
            else:
                self.generator.send(
                    (StatusCodeEnum.DISPATCH_EXCEPTION, ExcInfo(exception, tb))
                )
        except StopIteration:
            pass

    def afterExecution(
        self,
        interface: "DispatcherInterface",
        exception: Optional[Exception],
        tb: Optional[TracebackType],
    ):
        try:
            if not tb:
                self.generator.send((StatusCodeEnum.EXECUTION_COMPLETED, None))
            else:
                self.generator.send(
                    (StatusCodeEnum.EXECUTION_EXCEPTION, ExcInfo(exception, tb))
                )
        except StopIteration:
            pass
