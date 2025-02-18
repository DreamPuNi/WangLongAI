import threading
from typing import Dict
from common.dequeue import Dequeue
from collections import defaultdict
from common.log import logger
from config import conf
from bridge.context import Context

class MessageBuffer:
    """这里是实现的消息缓冲器，实现在消息通道类，主要是用来合并消息"""
    def __init__(self, channel_class):
        # 使用线程安全的锁
        self.lock = threading.Lock()
        # 存储各会话的缓冲队列和计时器
        self.buffers: Dict[str, Dict[str, 'buffer']] = defaultdict(lambda: {
            'queue': [],
            'timer': None
        })
        self.channnel = channel_class

    def add_message(self, context):
        """添加消息到缓冲队列并重置计时器"""
        # 使用session_id作为会话标识
        key = context.kwargs['session_id']
        wxid_black_wxid = conf().get("wxid_black_list")
        if key not in wxid_black_wxid:
            with self.lock:
                buffer = self.buffers[key]
                buffer['queue'].append(context)

                # 取消已有计时器
                if buffer['timer'] is not None:
                    buffer['timer'].cancel()

                # 创建新计时器
                buffer['timer'] = threading.Timer(10.0, self._process, args=[key])
                buffer['timer'].start()
                logger.info("Reset timer and add message {} wait for {} seconds.".format(key,"10"))
        else:
            logger.info("User {} has been transfer to manual.".format(key))

    def _process(self, key):
        """处理指定会话的消息"""
        with self.lock:
            if key not in self.buffers:
                return

            buffer = self.buffers.pop(key)
            contexts = buffer['queue']

            if not contexts:
                return

            # 合并消息并发送
            merged = self._merge_contexts(contexts)

            if key not in self.channnel.sessions:  # 如果是新的会话
                self.channnel.sessions[key] = [
                    Dequeue(),
                    threading.BoundedSemaphore(conf().get("concurrency_in_session", 4)),
                ]

            self.channnel.sessions[key][0].put(merged)

    def _merge_contexts(self, contexts):
        """合并多个上下文对象"""
        base = contexts[0]

        # 验证所有上下文的一致性，注意在这里放上异常处理
        for ctx in contexts[1:]:
            if ctx.type != base.type or {k: v for k,v in ctx.kwargs.items() if k!='msg'} != {k:v for k,v in base.kwargs.items() if k!='msg'}:
                logger.error("The context from {} parameters are inconsistent and cannot be merged.".format(contexts[0].kwargs['session_id']))
                #for con in contexts:
                #    print("====context-01====",con)
                raise ValueError()

        # 拼接消息内容
        merged_content = "。".join(ctx.content for ctx in contexts)

        # 创建新上下文对象
        return Context(
            type=base.type,
            content=merged_content,
            kwargs=base.kwargs.copy()
        )