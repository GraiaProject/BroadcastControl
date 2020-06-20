async def async_enumerate(iterable, start: int = 0):
    count = start
    async for i in iterable:
        yield (count, i)
        count += 1