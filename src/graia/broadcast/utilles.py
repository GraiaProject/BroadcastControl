from iterwrapper import IterWrapper
from typing import Callable, Any

async def async_enumerate(iterable, start: int = 0):
    count = start
    async for i in iterable:
        yield (count, i)
        count += 1

def iw_group(iw: IterWrapper, key: Callable[[Any], Any]):
    temp = {}
    for i in iw:
        k = key(i)
        temp.setdefault(k, [])
        temp[k].append(i)
    return IterWrapper(temp.values()).map(list)