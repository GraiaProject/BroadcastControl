from typing import Any, Callable, Dict, List, TypeVar

from ..typing import DEFAULT_LIFECYCLE_NAMES, T_Dispatcher

T = TypeVar("T")
I = TypeVar("I")

LF_TEMPLATE = {i: list() for i in DEFAULT_LIFECYCLE_NAMES}


class DII_NestableIterable:
    __slots__ = ("iterable", "indexes")

    iterable: List
    indexes: List

    def __init__(self, iterable: List) -> None:
        self.iterable = iterable
        self.indexes = [[0, 0]]

    def __iter__(self) -> T_Dispatcher:
        dis_set_index, dis_index = self.indexes[-1]
        dis_set_index_offset = dis_set_index + (dis_set_index and 1)
        dis_index_offset = dis_index + (dis_index and 1)

        current_indexes = [dis_set_index_offset, dis_index_offset]
        self.indexes.append(current_indexes)

        for content in self.iterable[dis_set_index_offset:]:
            for i in content[dis_index_offset:]:
                yield i
                current_indexes[1] += 1
            current_indexes[0] += 1

        self.indexes.pop()


class ExecutionContext:
    __slots__ = ("event", "lifecycle_refs", "dispatchers")

    lifecycle_refs: Dict[str, List[Callable]]
    dispatchers: List[T_Dispatcher]

    def __init__(self, dispatchers: List[T_Dispatcher]) -> None:
        self.dispatchers = dispatchers

        self.lifecycle_refs = {i: [] for i in DEFAULT_LIFECYCLE_NAMES}


class ParameterContext:
    __slots__ = ("name", "annotation", "default", "dispatchers", "path")

    name: str
    annotation: Any
    default: Any

    dispatchers: List[T_Dispatcher]

    def __init__(self, name, annotation, default, dispatchers, using_path) -> None:
        self.name = name
        self.annotation = annotation
        self.default = default
        self.dispatchers = dispatchers
        self.path = DII_NestableIterable(using_path)

    def __repr__(self) -> str:
        return (
            "<ParameterContext name={0} annotation={1} default={2} locald={3}".format(
                self.name, self.annotation, self.default, self.dispatchers
            )
        )
