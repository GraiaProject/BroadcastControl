from typing import Any, Callable


class Decorator:
    target: Callable[[Any], Any]
    pre: bool = False

    def __init__(self, target, pre=False):
        super().__init__(target=target, pre=pre)
