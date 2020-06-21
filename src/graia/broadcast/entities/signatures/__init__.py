from typing import Any

from pydantic import BaseModel  # pylint: disable=no-name-in-module


class ObjectContainer(BaseModel):
    target: Any

    def __init__(self, content: Any = None):
        if content.__class__ is self.__class__:
            content = content.target
        super().__init__(target=content)

class Force(ObjectContainer):
    """用于转义在本框架中特殊部分的特殊值

    例如：Dispatcher 内的 None 会被看作一个表示继续向下查阅 dispatcher, 而某些时候我们确实是需要传递 None 的，
    这时候可以用本标识来保证 None 被顺利作为一个参数传入。
    """

class RemoveMe(ObjectContainer):
    """当本标识的实例为一受 Executor 影响的 Listener 返回值时,
    Executor 会尝试在当前 Broadcast 实例中找出并删除本 Listener 实例.
    """
    