# Broadcast Control for Graia Framework

## 这是什么？
一个高性能，高可扩展性，设计简洁，基于 `asyncio` 的事件系统，为 `Graia Framework` 设计。

## 安装
### 从 PyPI 安装
``` bash
pip install graia-broadcast
# 或者使用 poetry
poetry add graia-broadcast
```

# Example

```python
from graia.broadcast import Dispatchable, BaseDispatcher, Broadcast
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

class ExampleEvent(Dispatchable):
    class Dispatcher(BaseDispatcher):
        def catch(interface: "DispatcherInterface"):
            if interface.annotation is str:
                return "ok, i'm."

broadcast = Broadcast()

@broadcast.receiver("ExampleEvent") # or just receiver(ExampleEvent)
async def event_listener(maybe_you_are_str: str):
    print(maybe_you_are_str) # <<< ok, i'm

async def main():
    broadcast.postEvent(ExampleEvent()) # sync call is allowed.
    await asyncio.sleep(0.1) # to solve event task.

loop.run_until_complete(main())
```

## 开源协议
本实现以 MIT 为开源协议。
