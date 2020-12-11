from typing import Any
from graia.broadcast.entities.event import BaseEvent
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.entities.listener import Listener
from graia.broadcast import Broadcast
from graia.broadcast.entities.decorater import Decorater
from graia.broadcast.builtin.decoraters import Depend, Middleware
from graia.broadcast.interfaces.decorater import DecoraterInterface
from graia.broadcast.exceptions import PropagationCancelled
from graia.broadcast.interrupt import InterruptControl
from graia.broadcast.interrupt.waiter import Waiter
import random
from devtools import debug
import asyncio
import time
import objgraph
import copy
import functools

from graia.broadcast.utilles import dispatcher_mixin_handler

#print(objgraph.most_common_types(20))

class D1(BaseDispatcher):
    @staticmethod
    def catch(interface: DispatcherInterface):
        if interface.annotation == "123":
            return random.random()

class D2(BaseDispatcher):
    mixin = [D1]
    @staticmethod
    async def catch(interface: DispatcherInterface):
        if interface.annotation == "13":
            r = await interface.lookup_param(interface.name, "123", interface.default)
            return r

class TestEvent(BaseEvent):
    class Dispatcher(BaseDispatcher):
        mixin = [D2]

        @staticmethod
        def catch(interface: DispatcherInterface):
            if interface.name == "u":
                yield 1
            elif interface.annotation == str:
                yield 12

        @staticmethod
        def afterDispatch(interface: "IDispatcherInterface"):
            print("in ad.")

event = TestEvent()
loop = asyncio.get_event_loop()
#loop.set_debug(True)
broadcast = Broadcast(loop=loop, debug_flag=True)
inc = InterruptControl(broadcast)

i = 0
l = asyncio.Lock()

@broadcast.receiver(TestEvent)
async def r(u, v: str, p: "123"):
    #print("???")
    global i
    i += 1

async def main():
    """
    start = time.time()
    print("将在 5 s 后开始测试.")
    for i in range(1, 6):
        print(i)
        await asyncio.sleep(1)
    print("测试开始.", start)
    event = TestEvent()
    for _ in range(10):
        broadcast.postEvent(event)
    await broadcast.Executor(r, event)
    end = time.time()
    print(f"事件广播完毕, 总共 10000 个, 当前时间: {end}, 用时: {end - start - 5}")
    """

    event = TestEvent()
    
    #await asyncio.gather(*[broadcast.layered_scheduler(
    #    listener_generator=broadcast.default_listener_generator(event.__class__),
    #    event=event,
    #) for _ in range(100)])
    for _ in range(1):
        broadcast.postEvent(event)

    #input()
    #debug(listener.dispatcher_statistics)
    #print(i)
    """
    def post_event():
        print("开始 post event")
        broadcast.postEvent(TestEvent())
    loop.call_later(6, post_event)
    print("已提交, 将在 6s 后 post event")
    #print(await inc.wait(ExampleWaiter()))

    @Waiter.create_using_function([TestEvent])
    def waiter(event: TestEvent):
        print(event)
        #return event
    
    print(await inc.wait(waiter))
    print("可能成功了...结果已经打印")"""

loop.run_until_complete(main())
loop.run_until_complete(asyncio.sleep(5))
#objgraph.show_most_common_types(30)
#time.sleep(30)
#tasks = bjgraph.by_type('Task')
#print(len(tasks), i)
#print(objgraph.find_ref_chain(tasks[0], objgraph.is_proper_module))
#debug(tasks)
#import pdb; pdb.set_trace()