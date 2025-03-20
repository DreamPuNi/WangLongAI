import os
import re
import threading
import time
from asyncio import CancelledError
from concurrent.futures import Future, ThreadPoolExecutor
from bridge.context import *
from bridge.reply import *
from channel.channel import Channel
from common.dequeue import Dequeue
from common import memory
from channel.message_buffer import MessageBuffer
from config import conf
from plugins import *

try:
    from voice.audio_convert import any_to_wav
except Exception as e:
    pass

handler_pool = ThreadPoolExecutor(max_workers=8)  # 处理消息的线程池


# 抽象类, 它包含了与消息通道无关的通用处理逻辑
class ChatChannel(Channel):
    name = None  # 登录的用户名
    user_id = None  # 登录的用户id
    futures = {}  # 记录每个session_id提交到线程池的future对象, 用于重置会话时把没执行的future取消掉，正在执行的不会被取消
    sessions = {}  # 用于控制并发，每个session_id同时只能有一个context在处理
    lock = threading.Lock()  # 用于控制对sessions的访问

    def __init__(self):
        self.message_buffer = MessageBuffer(self)
        _thread = threading.Thread(target=self.consume)
        _thread.setDaemon(True)
        _thread.start()

    def _compose_context(self, ctype: ContextType, content, **kwargs):
        """
        对消息进行处理，主要是提取消息信息，过滤黑名单，判断是否激活AI，去除@内容，确保消息正确进入后续处理流程。并根据设置决定返回的消息类型（文本、画图、语音）

        Args:
            ctype (ContextType): 消息的类型，决定上下文的构造方式。
            content: 消息内容，可能包含文本、语音或其他信息。
            **kwargs: 其他附加的参数，用于进一步配置上下文。

        Returns:
            处理后的context
        """
        context = Context(ctype, content)
        context.kwargs = kwargs
        if ctype == ContextType.ACCEPT_FRIEND:  # 如果类型是同意好友请求，那么直接返回消息类型和上下文
            return context

        """
        context首次传入时，origin_ctype是None,
        引入的起因是：当输入语音时，会嵌套生成两个context，第一步语音转文本，第二步通过文本生成文字回复。
        origin_ctype用于第二步文本回复时，判断是否需要匹配前缀，如果是私聊的语音，就不需要匹配前缀
        """
        if "origin_ctype" not in context:
            context["origin_ctype"] = ctype

        first_in = "receiver" not in context  # context首次传入时，receiver是None，根据类型设置receiver
        # 群名匹配过程，设置session_id和receiver
        if first_in:  # context首次传入时，receiver是None，根据类型设置receiver
            """
            让不同类型的消息都能合理处理，并为后续对话提供正确的 session_id 和 receiver。

            ✔ 主要完成的工作：

                初始化 context，注入 OpenAI API Key 和 GPT 设置信息。
                判断是群聊还是单聊，并分别处理：
                    群聊：
                        先检查白名单，如果不在白名单，直接跳过。
                        处理 session_id，决定是否群聊共享对话。
                        记录 receiver 作为群聊 ID。
                    单聊：
                        session_id 直接设为对方 ID，receiver 设为对方 ID。
                触发事件，允许插件修改 context 或拦截消息处理。
                检查是否是自己发送的消息，并根据配置决定是否跳过处理。

            ✔ 最终目标：
            确保消息正确地进入后续处理流程，同时提供群聊白名单、共享会话、插件拦截、自身消息过滤等功能
            """
            config = conf()
            cmsg = context["msg"]
            user_data = conf().get_user_data(cmsg.from_user_id)
            context["openai_api_key"] = user_data.get("openai_api_key")
            context["gpt_model"] = user_data.get("gpt_model")
            if context.get("isgroup", False):  # 如果是群聊
                group_name = cmsg.other_user_nickname
                group_id = cmsg.other_user_id
                context["group_name"] = group_name

                group_name_white_list = config.get("group_name_white_list", [])
                group_name_keyword_white_list = config.get("group_name_keyword_white_list", [])
                if any(
                        [
                            group_name in group_name_white_list,
                            "ALL_GROUP" in group_name_white_list,
                            check_contain(group_name, group_name_keyword_white_list),
                        ]
                ):  # 如果群聊名称或群聊名称中包含白名单中的关键词，或者白名单中包含 "ALL_GROUP"，就允许继续处理。
                    group_chat_in_one_session = conf().get("group_chat_in_one_session", [])
                    session_id = f"{cmsg.actual_user_id}@@{group_id}"  # 当群聊未共享session时，session_id为user_id与group_id的组合，用于区分不同群聊以及单聊
                    context["is_shared_session_group"] = False  # 默认为非共享会话群
                    if any(
                            [
                                group_name in group_chat_in_one_session,
                                "ALL_GROUP" in group_chat_in_one_session,
                            ]
                    ):  # 是否需要多个群聊共享对话
                        session_id = group_id
                        context["is_shared_session_group"] = True  # 如果是共享会话群，设置为True
                else:
                    logger.debug(f"No need reply, groupName not in whitelist, group_name={group_name}")
                    return None
                context["session_id"] = session_id
                context["receiver"] = group_id
            else:  # 如果是单聊
                context["session_id"] = cmsg.other_user_id
                context["receiver"] = cmsg.other_user_id
            e_context = PluginManager().emit_event(
                EventContext(Event.ON_RECEIVE_MESSAGE, {"channel": self, "context": context}))
            context = e_context["context"]
            if e_context.is_pass() or context is None:
                return context
            if cmsg.from_user_id == self.user_id and not config.get("trigger_by_self", True):
                logger.debug("[chat_channel]self message skipped")
                return None

        if ctype == ContextType.TEXT:
            """
            判断AI是否被唤醒，唤醒的形式，并过滤掉黑名单用户的消息，然后去除唤醒内容如@等，保证消息纯净，最后判断回复方式是文本还是语音
            """
            nick_name_black_list = conf().get("nick_name_black_list", [])
            wxid_black_list = conf().get("wxid_black_list", [])
            if context.get("isgroup", False):  # 群聊处理，判断是否唤醒了AI，如果唤醒了，就去掉@内容，并继续处理消息。
                match_prefix = check_prefix(content, conf().get("group_chat_prefix"))
                match_contain = check_contain(content, conf().get("group_chat_keyword"))
                flag = False
                if context["msg"].to_user_id != context["msg"].actual_user_id:  # 去除消息中的所有@
                    if match_prefix is not None or match_contain is not None:  # 如果消息满足前缀匹配或包含关键词，则将 flag 设为 True，表示这条消息应该被处理。
                        flag = True
                        if match_prefix:
                            content = content.replace(match_prefix, "",
                                                      1).strip()  # 去除匹配到的前缀，确保后续处理的 content 只包含真正的聊天内容，而不会受到触发前缀的干扰。
                    if context["msg"].is_at:  # 如果机器人被@
                        nick_name = context["msg"].actual_user_nickname
                        if nick_name and nick_name in nick_name_black_list:  # 黑名单过滤
                            logger.warning(f"[chat_channel] Nickname {nick_name} in In BlackList, ignore")
                            return None

                        logger.info("[chat_channel]receive group at")
                        if not conf().get("group_at_off", False):  # 判断是否开启群聊@功能了，如果开启就设置该消息需要处理
                            flag = True
                        self.name = self.name if self.name is not None else ""  # 部分渠道self.name可能没有赋值
                        pattern = f"@{re.escape(self.name)}(\u2005|\u0020)"  # 去除消息内容中的 @ 机器人，确保后续处理时不会带有@信息。
                        subtract_res = re.sub(pattern, r"", content)
                        if isinstance(context["msg"].at_list, list):  # 去除消息中所有被@的用户名，确保最终处理的 content 不包含 @某人 这样的内容。
                            for at in context["msg"].at_list:
                                pattern = f"@{re.escape(at)}(\u2005|\u0020)"
                                subtract_res = re.sub(pattern, r"", subtract_res)
                        if subtract_res == content and context[
                            "msg"].self_display_name:  # 确保无论用户 @ 机器人的用户名还是群昵称，最终 content 只留下真正的聊天内容。
                            # 前缀移除后没有变化，使用群昵称再次移除
                            pattern = f"@{re.escape(context['msg'].self_display_name)}(\u2005|\u0020)"
                            subtract_res = re.sub(pattern, r"", content)
                        content = subtract_res
                if not flag:  # 语音中没有机器人唤醒字，则略过处理
                    if context["origin_ctype"] == ContextType.VOICE:
                        logger.info("[chat_channel]receive group voice, but checkprefix didn't match")
                    return None
            else:  # 单聊，过滤黑名单用户，处理消息前缀和@，并且将所有的语音消息标记为直接处理
                nick_name = context["msg"].from_user_nickname
                wxid = context["receiver"]

                if nick_name and nick_name in nick_name_black_list:
                    if wxid and wxid in wxid_black_list:
                        # 黑名单过滤
                        logger.warning(f"[chat_channel] Nickname '{nick_name}' in In BlackList, ignore")
                        return None

                match_prefix = check_prefix(content, conf().get("single_chat_prefix", [""]))
                if match_prefix is not None:  # 判断如果匹配到自定义前缀，则返回过滤掉前缀+空格后的内容
                    content = content.replace(match_prefix, "", 1).strip()
                elif context["origin_ctype"] == ContextType.VOICE:  # 如果源消息是私聊的语音消息，允许不匹配前缀，放宽条件
                    pass
                else:
                    return None
            content = content.strip()
            img_match_prefix = check_prefix(content, conf().get("image_create_prefix", [""]))
            if img_match_prefix:  # 根据是否有画图的关键字来判断并处理消息类型，如果是画图请求，就去掉前缀并设置类型为画图。否则设置为文本类型
                content = content.replace(img_match_prefix, "", 1)
                context.type = ContextType.IMAGE_CREATE
            else:
                context.type = ContextType.TEXT
            context.content = content.strip()
            if "desire_rtype" not in context and conf().get(  # 判断是否使用语音回复
                    "always_reply_voice") and ReplyType.VOICE not in self.NOT_SUPPORT_REPLYTYPE:
                context["desire_rtype"] = ReplyType.VOICE
        elif context.type == ContextType.VOICE:
            if "desire_rtype" not in context and conf().get(
                    "voice_reply_voice") and ReplyType.VOICE not in self.NOT_SUPPORT_REPLYTYPE:
                context["desire_rtype"] = ReplyType.VOICE
        return context

    def _handle(self, context: Context):
        """
        处理消息并产生回复后发送。先检查是否需要进行回复，然后发出生成reply请求，得到reply之后进行包装reply，最后执行发送reply

        Args:
            context: 需要让AI处理的消息
        """
        if context is None or not context.content:
            return
        logger.debug("[chat_channel] ready to handle context: {}".format(context))
        reply = self._generate_reply(context)  # reply的构建步骤
        logger.debug("[chat_channel] ready to decorate reply: {}".format(reply))
        if reply and reply.content:  # reply的包装步骤
            reply = self._decorate_reply(context, reply)
            self._send_reply(context, reply)  # reply的发送步骤

    def _generate_reply(self, context: Context, reply: Reply = Reply()) -> Reply:
        """
        针对接收到的不同类型的消息分别进行处理并返回处理结果

        Args:
            context: 需要进行处理的内容
            reply: 供递归调用使用

        Return:
            reply: AI处理后的回复
        """
        e_context = PluginManager().emit_event(
            EventContext(
                Event.ON_HANDLE_CONTEXT,
                {"channel": self, "context": context, "reply": reply},
            )
        )
        reply = e_context["reply"]
        if not e_context.is_pass():
            logger.debug(
                "[chat_channel] ready to handle context: type={}, content={}".format(context.type, context.content))
            if context.type == ContextType.TEXT or context.type == ContextType.IMAGE_CREATE:  # 文字和图片消息
                context["channel"] = e_context["channel"]
                reply = super().build_reply_content(context.content, context)
            elif context.type == ContextType.VOICE:  # 语音消息
                cmsg = context["msg"]
                cmsg.prepare()
                file_path = context.content
                wav_path = os.path.splitext(file_path)[0] + ".wav"
                try:
                    any_to_wav(file_path, wav_path)
                except Exception as e:  # 转换失败，直接使用mp3，对于某些api，mp3也可以识别
                    logger.warning("[chat_channel]any to wav error, use raw path. " + str(e))
                    wav_path = file_path
                # 语音识别
                reply = super().build_voice_to_text(wav_path)
                print(f"【chat_channel】=====reply: {reply}")
                # 删除临时文件
                try:
                    os.remove(file_path)
                    if wav_path != file_path:
                        os.remove(wav_path)
                except Exception as e:
                    pass
                    # logger.warning("[chat_channel]delete temp file error: " + str(e))

                if reply.type == ReplyType.TEXT:
                    new_context = self._compose_context(ContextType.TEXT, reply.content, **context.kwargs)
                    # 添加了语音消息合并到消息列表并继承上下文的操作
                    session_id = new_context.kwargs.get("session_id")
                    if session_id:
                        conf().user_data = conf().get_user_data(session_id)
                        conf().user_data["history"].append(
                            {"user": new_context.content}
                        )
                        conf().save_user_datas()
                        new_context.content = str(conf().user_datas[session_id]["history"])

                    if new_context:
                        reply = self._generate_reply(new_context)
                    else:
                        return
                    print(f"【chat_channel】=====new_context: {new_context}")
                    print(f"【chat_channel】=====reply: {reply}")
            elif context.type == ContextType.IMAGE:  # 图片消息，当前仅做下载保存到本地的逻辑
                memory.USER_IMAGE_CACHE[context["session_id"]] = {
                    "path": context.content,
                    "msg": context.get("msg")
                }
            elif context.type == ContextType.ACCEPT_FRIEND:  # 好友申请，匹配字符串
                reply = self._build_friend_request_reply(context)
            elif context.type == ContextType.SHARING:  # 分享信息，当前无默认逻辑
                pass
            elif context.type == ContextType.FUNCTION or context.type == ContextType.FILE:  # 文件消息及函数调用等，当前无默认逻辑
                pass
            else:
                logger.warning("[chat_channel] unknown context type: {}".format(context.type))
                return
        return reply

    def _decorate_reply(self, context: Context, reply: Reply) -> Reply:
        """
        接收一个生成的回复并根据不同的条件进行装饰，包括转换回复类型、修改内容格式、处理错误类型等。

        Args:
            context: 需要处理的内容
            reply: 回复内容，供递归调用使用

        Return:
            reply: 装饰后的回复
        """
        if reply and reply.type:
            e_context = PluginManager().emit_event(
                EventContext(
                    Event.ON_DECORATE_REPLY,
                    {"channel": self, "context": context, "reply": reply},
                )
            )
            reply = e_context["reply"]
            desire_rtype = context.get("desire_rtype")
            if not e_context.is_pass() and reply and reply.type:
                if reply.type in self.NOT_SUPPORT_REPLYTYPE:
                    logger.error("[chat_channel]reply type not support: " + str(reply.type))
                    reply.type = ReplyType.ERROR
                    reply.content = "不支持发送的消息类型: " + str(reply.type)

                if reply.type == ReplyType.TEXT:
                    reply_text = reply.content
                    if desire_rtype == ReplyType.VOICE and ReplyType.VOICE not in self.NOT_SUPPORT_REPLYTYPE:
                        reply = super().build_text_to_voice(reply.content)
                        return self._decorate_reply(context, reply)
                    if context.get("isgroup", False):
                        if not context.get("no_need_at", False):
                            reply_text = "@" + context["msg"].actual_user_nickname + "\n" + reply_text.strip()
                        reply_text = conf().get("group_chat_reply_prefix", "") + reply_text + conf().get(
                            "group_chat_reply_suffix", "")
                    else:
                        reply_text = conf().get("single_chat_reply_prefix", "") + reply_text + conf().get(
                            "single_chat_reply_suffix", "")
                    reply.content = reply_text
                elif reply.type == ReplyType.ERROR or reply.type == ReplyType.INFO:
                    reply.content = "[" + str(reply.type) + "]\n" + reply.content
                elif reply.type == ReplyType.IMAGE_URL or reply.type == ReplyType.VOICE or reply.type == ReplyType.IMAGE or reply.type == ReplyType.FILE or reply.type == ReplyType.VIDEO or reply.type == ReplyType.VIDEO_URL:
                    pass
                elif reply.type == ReplyType.ACCEPT_FRIEND:
                    pass
                else:
                    logger.error("[chat_channel] unknown reply type: {}".format(reply.type))
                    return
            if desire_rtype and desire_rtype != reply.type and reply.type not in [ReplyType.ERROR, ReplyType.INFO]:
                logger.warning("[chat_channel] desire_rtype: {}, but reply type: {}".format(context.get("desire_rtype"),
                                                                                            reply.type))
            return reply

    def _send_reply(self, context: Context, reply: Reply):
        """
        检查生成的回复，符合要求时执行发送

        Args:
            context: 需要发送的内容
            reply: 回复内容，供递归调用使用
        """
        if reply and reply.type:
            e_context = PluginManager().emit_event(
                EventContext(
                    Event.ON_SEND_REPLY,
                    {"channel": self, "context": context, "reply": reply},
                )
            )
            reply = e_context["reply"]
            if not e_context.is_pass() and reply and reply.type:
                logger.debug("[chat_channel] ready to send reply: {}, context: {}".format(reply, context))
                self._send(reply, context)

    def _send(self, reply: Reply, context: Context, retry_cnt=0):
        """
        发送回复函数

        Args:
            reply: 回复内容，供递归调用使用
            context: 需要发送的内容
            retry_cnt: 重试次数
        """
        try:
            self.send(reply, context)
        except Exception as e:
            logger.error("[chat_channel] sendMsg error: {}".format(str(e)))
            if isinstance(e, NotImplementedError):
                return
            logger.exception(e)
            if retry_cnt < 2:
                time.sleep(3 + 3 * retry_cnt)
                self._send(reply, context, retry_cnt + 1)

    def _build_friend_request_reply(self, context):
        """
        处理好友申请，当好友请求中包含accept_friend_commands中的内容时自动通过

        Args:
            context: 需要进行处理的内容

        Return:
            reply: 通过好友请求的消息体
        """
        if isinstance(context.content, dict) and "Content" in context.content:
            logger.info("friend request content: {}".format(context.content["Content"]))
            return Reply(type=ReplyType.ACCEPT_FRIEND, content=True)

            #if context.content["Content"] in conf().get("accept_friend_commands", []):
            #    return Reply(type=ReplyType.ACCEPT_FRIEND, content=True)
            #else:
            #    return Reply(type=ReplyType.ACCEPT_FRIEND, content=False)

        else:
            logger.error("Invalid context content: {}".format(context.content))
            return None

    def _success_callback(self, session_id, **kwargs):
        """线程正常结束时的回调函数"""
        logger.debug("Worker return success, session_id = {}".format(session_id))

    def _fail_callback(self, session_id, exception, **kwargs):
        """线程异常结束时的回调函数"""
        logger.exception("Worker return exception: {}".format(exception))

    def _thread_pool_callback(self, session_id, **kwargs):
        """
        确保线程池中的每个任务都能正确处理成功和失败情况，并且能够安全地释放资源。

        Args:
            session_id: 当前会话标识符
            kwargs: 其他相关参数

        Return:
            func: 回调函数
        """

        def func(worker: Future):
            try:
                worker_exception = worker.exception()  # 获取任务执行过程中是否抛出了异常。
                if worker_exception:
                    self._fail_callback(session_id, exception=worker_exception, **kwargs)
                else:
                    self._success_callback(session_id, **kwargs)

            except CancelledError as e:
                logger.info("Worker cancelled, session_id = {}".format(session_id))
            except Exception as e:
                logger.exception("Worker raise exception: {}".format(e))
            with self.lock:  # 进行线程安全操作，确保在修改共享资源时不会发生竞争条件。
                self.sessions[session_id][1].release()  # 在任务完成后，无论成功还是失败，都会释放该锁，以允许其他线程继续执行。

        return func

    def produce(self, context: Context):
        """
        使用锁保护，处理消息队列，如果是新的会话，就创建对话，如果是管理命令，就优先处理，否则正常处理

        Args:
            context: 当前对话信息
        """
        session_id = context.get("session_id", 0)

        with self.lock:
            if session_id not in self.sessions:
                self.sessions[session_id] = [
                    Dequeue(),
                    threading.BoundedSemaphore(conf().get("concurrency_in_session", 4))
                ]
            if context.type == ContextType.TEXT and context.content.startswith("#"):  # 如果是管理命令
                if session_id not in self.sessions:  # 如果是新的会话
                    self.sessions[session_id] = [
                        Dequeue(),
                        threading.BoundedSemaphore(conf().get("concurrency_in_session", 4)),
                    ]
                self.sessions[session_id][0].putleft(context)  # 优先处理管理命令
            elif context.type == ContextType.TEXT: # 仅对文本进行消息缓冲
                self.message_buffer.add_message(context)
            else:
                self.sessions[session_id][0].put(context)

    def consume(self):
        """主要是处理会话队列中的任务并管理它们的执行。它会不断地从每个会话的任务队列中取出任务进行处理，并管理任务的执行状态和资源释放。"""
        while True:
            with self.lock:  # 线程安全的条件下获取所有的session id
                session_ids = list(self.sessions.keys())
            for session_id in session_ids:  # 遍历每个session_id
                with self.lock:
                    context_queue, semaphore = self.sessions[session_id]
                """
                从 self.sessions 中取出当前会话的任务队列（context_queue）和信号量（semaphore）。
                如果当前信号量未被占用（blocking=False），则允许线程继续执行；否则，当前线程会跳过，不会继续处理该会话。

                每个会话都有一个 BoundedSemaphore，它控制同一会话中最多同时可以处理多少个任务。如果信号量被占用（意味着有任务正在处理），则当前线程会跳过，不会取出新的任务。
                """
                if semaphore.acquire(blocking=False):  # 等线程处理完毕才能删除
                    if not context_queue.empty():
                        context = context_queue.get()  # 如果队列不为空，则从队列中取出一个任务（context）。
                        logger.debug("[chat_channel] consume context: {}".format(context))
                        # 使用线程池（handler_pool）提交任务处理。self._handle 是处理任务的主逻辑，context 是任务内容。
                        future: Future = handler_pool.submit(self._handle, context)
                        # 为 future 添加回调函数（_thread_pool_callback）
                        future.add_done_callback(self._thread_pool_callback(session_id, context=context))
                        with self.lock:
                            if session_id not in self.futures:
                                self.futures[session_id] = []
                            self.futures[session_id].append(future)
                    elif semaphore._initial_value == semaphore._value + 1:  # 除了当前，没有任务再申请到信号量，说明所有任务都处理完毕
                        with self.lock:
                            self.futures[session_id] = [t for t in self.futures[session_id] if not t.done()]
                            assert len(self.futures[session_id]) == 0, "thread pool error"
                            del self.sessions[session_id]
                    else:
                        semaphore.release()
            time.sleep(0.2)

    def cancel_session(self, session_id):
        """取消session_id对应的所有任务，只能取消排队的消息和已提交线程池但未执行的任务"""
        with self.lock:
            if session_id in self.sessions:
                for future in self.futures[session_id]:
                    future.cancel()
                cnt = self.sessions[session_id][0].qsize()
                if cnt > 0:
                    logger.info("Cancel {} messages in session {}".format(cnt, session_id))
                self.sessions[session_id][0] = Dequeue()

    def cancel_all_session(self):
        """取消所有任务"""
        with self.lock:
            for session_id in self.sessions:
                for future in self.futures[session_id]:
                    future.cancel()
                cnt = self.sessions[session_id][0].qsize()
                if cnt > 0:
                    logger.info("Cancel {} messages in session {}".format(cnt, session_id))
                self.sessions[session_id][0] = Dequeue()


def check_prefix(content, prefix_list):
    """检查 content 字符串的开头是否包含 prefix_list 中的任意一个前缀（prefix）"""
    if not prefix_list:
        return None
    for prefix in prefix_list:
        if content.startswith(prefix):
            return prefix
    return None


def check_contain(content, keyword_list):
    """检查 content 中是否包含 keyword_list 中的任意一个关键词"""
    if not keyword_list:
        return None
    for ky in keyword_list:
        if content.find(ky) != -1:
            return True
    return None
