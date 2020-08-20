from typing import Any, Callable

from pydantic import BaseModel  # pylint: disable=no-name-in-module


class Decorater:
    target: Callable[[Any], Any]
    pre: bool = False

    def __init__(self, target, pre=False):
        super().__init__(target=target, pre=pre)
