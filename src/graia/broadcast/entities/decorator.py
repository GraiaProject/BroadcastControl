from typing import Any, Callable


class Decorator:
    target: Callable[[Any], Any]
    pre: bool = False
