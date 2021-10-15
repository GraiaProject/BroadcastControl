from abc import ABCMeta, abstractmethod
from types import TracebackType
from typing import TYPE_CHECKING, List, Optional, Type, Union

if TYPE_CHECKING:
    from ..interfaces.dispatcher import DispatcherInterface


class BaseDispatcher(metaclass=ABCMeta):
    """所有非单函数型 Dispatcher 的基类, 用于为参数解析提供可扩展的支持."""

    mixin: List[Union["BaseDispatcher", Type["BaseDispatcher"]]]
    """声明该 Dispatcher 所包含的来自其他 Dispatcher 提供的参数解析支持,
    若某参数该 Dispatcher 无法解析, 将跳转到该列表中并交由其中的 Dispatcher 进行解析,
    该列表中的 Dispatcher 全部被调用过且都不返回一有效值时才会将解析权交由其他的 Dispatcher.
    """

    @abstractmethod
    async def catch(self, interface: "DispatcherInterface"):
        """该方法可以是 `staticmethod`, `classmethod` 亦或是普通的方法/函数.
        唯一的要求是 `Dispatcher.catch` 获取到的必须为一可调用异步 Callable.

        Args:
            interface (DispatcherInterface): `Dispatcher` 服务的主要对象, 可以从其中获取以下信息:
             - 当前解析中的参数的信息;
             - 当前执行的信息, 比如正在处理的事件, `Listener`/`ExecTarget` etc.;
        """
        pass

    def afterDispatch(
        self,
        interface: "DispatcherInterface",
        exception: Optional[Exception],
        tb: Optional[TracebackType],
    ):
        """生命周期钩子: 在参数被解析完后被调用

        Args:
            interface (DispatcherInterface): `Dispatcher` 服务的主要对象, 可以从其中获取以下信息:
             - 当前解析中的参数的信息;
             - 当前执行的信息, 比如正在处理的事件, `Listener`/`ExecTarget` etc.;
            exception (Optional[Exception]): 可能存在的异常对象, 若为 None 则表示无异常被抛出, 执行顺利完成.
            tb (Optional[TracebackType]): 可能存在的异常堆栈对象, 若为 None 则表示无异常被抛出, 执行顺利完成.
        """
        pass

    def beforeExecution(self, interface: "DispatcherInterface"):
        """生命周期钩子: 在整个执行流程(包括参数解析)开始前被调用

        Args:
            interface (DispatcherInterface): `Dispatcher` 服务的主要对象, 可以从其中获取以下信息:
             - 当前解析中的参数的信息;
             - 当前执行的信息, 比如正在处理的事件, `Listener`/`ExecTarget` etc.;
        """
        pass

    def afterExecution(
        self,
        interface: "DispatcherInterface",
        exception: Optional[Exception],
        tb: Optional[TracebackType],
    ):
        """生命周期钩子: 在整个执行流程(包括参数解析)完成(包含因异常被抛出而退出)后被调用.

        Args:
            interface (DispatcherInterface): `Dispatcher` 服务的主要对象, 可以从其中获取以下信息:
             - 当前解析中的参数的信息;
             - 当前执行的信息, 比如正在处理的事件, `Listener`/`ExecTarget` etc.;
            exception (Optional[Exception]): 可能存在的异常对象, 若为 None 则表示无异常被抛出, 执行顺利完成.
            tb (Optional[TracebackType]): 可能存在的异常堆栈对象, 若为 None 则表示无异常被抛出, 执行顺利完成.
        """
        pass
