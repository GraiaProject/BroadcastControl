from abc import ABCMeta, abstractstaticmethod
from types import TracebackType
from typing import List, Optional


class BaseDispatcher(metaclass=ABCMeta):
    """所有非单函数型 Dispatcher 的基类, 用于为参数解析提供可扩展的支持."""

    always: bool
    "声明该 Dispatcher 是否应该在一次参数解析环节中至少被调用一次."

    mixin: List["BaseDispatcher"]
    """声明该 Dispatcher 所包含的来自其他 Dispatcher 提供的参数解析支持,
    若某参数该 Dispatcher 无法解析, 将跳转到该列表中并交由其中的 Dispatcher 进行解析,
    该列表中的 Dispatcher 全部被调用过且都不返回一有效值时才会将解析权交由其他的 Dispatcher.
    """

    @abstractstaticmethod
    async def catch(interface: "IDispatcherInterface"):
        """该方法可以是 `staticmethod`, `classmethod` 亦或是普通的方法/函数.
        唯一的要求是 `Dispatcher.catch` 获取到的必须为一可调用异步 Callable.

        Args:
            interface (IDispatcherInterface): `Dispatcher` 服务的主要对象, 可以从其中获取以下信息:
             - 当前解析中的参数的信息;
             - 当前执行的信息, 比如正在处理的事件, `Listener`/`ExecTarget` etc.;
        """
        pass

    def beforeDispatch(self, interface: "IDispatcherInterface"):
        """生命周期钩子: 在解析参数前被调用

        Args:
            interface (IDispatcherInterface): `Dispatcher` 服务的主要对象, 可以从其中获取以下信息:
             - 当前解析中的参数的信息;
             - 当前执行的信息, 比如正在处理的事件, `Listener`/`ExecTarget` etc.;
        """
        pass

    def afterDispatch(self, interface: "IDispatcherInterface"):
        """生命周期钩子: 在参数被解析完后被调用

        Args:
            interface (IDispatcherInterface): `Dispatcher` 服务的主要对象, 可以从其中获取以下信息:
             - 当前解析中的参数的信息;
             - 当前执行的信息, 比如正在处理的事件, `Listener`/`ExecTarget` etc.;
        """
        pass

    def beforeExecution(self, interface: "IDispatcherInterface"):
        """生命周期钩子: 在整个执行流程(包括参数解析)开始前被调用

        Args:
            interface (IDispatcherInterface): `Dispatcher` 服务的主要对象, 可以从其中获取以下信息:
             - 当前解析中的参数的信息;
             - 当前执行的信息, 比如正在处理的事件, `Listener`/`ExecTarget` etc.;
        """
        pass

    def afterExecution(
        self,
        interface: "IDispatcherInterface",
        exception: Optional[Exception],
        tb: Optional[TracebackType],
    ):
        """生命周期钩子: 在整个执行流程(包括参数解析)完成(包含因异常被抛出而退出)后被调用.

        Args:
            interface (IDispatcherInterface): `Dispatcher` 服务的主要对象, 可以从其中获取以下信息:
             - 当前解析中的参数的信息;
             - 当前执行的信息, 比如正在处理的事件, `Listener`/`ExecTarget` etc.;
            exception (Optional[Exception]): 可能存在的异常对象, 若为 None 则表示无异常被抛出, 执行顺利完成.
            tb (Optional[TracebackType]): 可能存在的异常堆栈对象, 若为 None 则表示无异常被抛出, 执行顺利完成.
        """
        pass

    def beforeTargetExec(self, interface: "IDispatcherInterface"):
        """生命周期钩子: 在参数解析完成后, 准备执行事件执行主体前被调用.

        Args:
            interface (IDispatcherInterface): `Dispatcher` 服务的主要对象, 可以从其中获取以下信息:
             - 当前解析中的参数的信息;
             - 当前执行的信息, 比如正在处理的事件, `Listener`/`ExecTarget` etc.;
        """
        pass

    def afterTargetExec(
        self,
        interface: "IDispatcherInterface",
        exception: Optional[Exception],
        tb: Optional[TracebackType],
    ):
        """生命周期钩子: 在事件执行主体被执行完成后被调用.

        Args:
            interface (IDispatcherInterface): `Dispatcher` 服务的主要对象, 可以从其中获取以下信息:
             - 当前解析中的参数的信息;
             - 当前执行的信息, 比如正在处理的事件, `Listener`/`ExecTarget` etc.;
            exception (Optional[Exception]): 可能存在的异常对象, 若为 None 则表示无异常被抛出, 执行顺利完成.
            tb (Optional[TracebackType]): 可能存在的异常堆栈对象, 若为 None 则表示无异常被抛出, 执行顺利完成.
        """
        pass

    def onActive(self, interface: "IDispatcherInterface"):
        """生命周期钩子: 在该 Dispatcher 可用于参数解析时被立即调用.

        Args:
            interface (IDispatcherInterface): `Dispatcher` 服务的主要对象, 可以从其中获取以下信息:
             - 当前解析中的参数的信息;
             - 当前执行的信息, 比如正在处理的事件, `Listener`/`ExecTarget` etc.;
        """
        pass


from graia.broadcast.abstract.interfaces.dispatcher import IDispatcherInterface
