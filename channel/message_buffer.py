import threading
from config import conf
from typing import Dict
from common.log import logger
from common.dequeue import Dequeue
from bridge.context import Context
from collections import defaultdict

class MessageBuffers:
    """根据配置动态选择消息缓冲器"""
    def __new__(cls, channel_class):
        if conf().get("channel_type") == "gewechat":
            return MessageBufferWithHistory(channel_class)
        # return MessageBufferWithoutHistory(channel_class)

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
                buffer['timer'] = threading.Timer(conf().get("message_buffer_second", 1), self._process, args=[key])
                buffer['timer'].start()
                logger.info("Reset timer and add message {} wait for {} seconds.".format(key,conf().get("message_buffer_second", 1)))
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

            # 把消息添加到history

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
                raise ValueError()

        # 拼接消息内容
        merged_content = "。".join(ctx.content for ctx in contexts)

        # 创建新上下文对象
        return Context(
            type=base.type,
            content=merged_content,
            kwargs=base.kwargs.copy()
        )

class MessageBufferWithHistory:
    """消息缓冲器，合并消息并控制发送时机"""

    def __init__(self, channel_class):
        self.lock = threading.Lock()
        self.all_tmp_history = defaultdict(list)  # 持久存储会话消息
        self.timers = {}  # 存储各会话的定时器
        self.channel = channel_class

    def add_message(self, context):
        """添加消息到缓冲队列并重置计时器"""
        key = context.kwargs['session_id']
        wxid_black_wxid = conf().get("wxid_black_list")

        if key not in wxid_black_wxid:
            with self.lock:
                self.all_tmp_history[key].append({"user": context})  # 直接存入历史消息
                # print("=========现在的全消息是：",self.all_tmp_history)
                # 取消已有计时器
                if key in self.timers:
                    self.timers[key].cancel()

                # 创建新计时器
                self.timers[key] = threading.Timer(
                    conf().get("message_buffer_second", 1),
                    self._process,
                    args=[key]
                )
                self.timers[key].start()

                logger.info(
                    f"Reset timer and add message {key} wait for {conf().get('message_buffer_second', 1)} seconds.")
        else:
            logger.info(f"User {key} has been transferred to manual.")

    def _process(self, key):
        """处理指定会话的消息"""
        with self.lock:
            if key not in self.all_tmp_history:
                return

            messages = self.all_tmp_history[key]  # 直接使用，不清空

            if not messages:
                return

            # 取第一个消息的 context 作为基础
            base_context = messages[0]["user"]

            # 创建新的 Context 对象
            merged_context = Context(
                type=base_context.type,
                content=messages,  # 这里用合并后的消息内容
                kwargs=base_context.kwargs.copy()
            )

            if key not in self.channel.sessions:  # 如果是新的会话
                self.channel.sessions[key] = [
                    Dequeue(),
                    threading.BoundedSemaphore(conf().get("concurrency_in_session", 4)),
                ]

            self.channel.sessions[key][0].put(merged_context)  # 发送合并后的 Context