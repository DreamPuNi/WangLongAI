import os
import re
import sys
import time
import jpype
import datetime
import threading
import pyperclip
import jpype.imports
from jpype.types import *
from common.log import logger
from dateutil.utils import today
from config import drag_sensitive
from config import conf, save_config
from bridge.reply import Reply, ReplyType
from channel.chat_channel import ChatChannel
from bridge.context import Context, ContextType
from channel.sikulix_wechat.sikulix_chat_message import SikuliXMessage

class SikuliXChannel(ChatChannel):
    def __init__(self, jvm_path):
        # 启动 JVM，并加载 sikulixapi.jar
        super().__init__()
        PROJECT_ROOT = sys.path[0]
        self.jvm_path = jvm_path
        self.sikulix_jar_path = os.path.join(PROJECT_ROOT,"lib","sikulix","sikulixide-2.0.5-win.jar")#
        jpype.startJVM(self.jvm_path, classpath=[self.sikulix_jar_path])
        from org.sikuli.script import Screen, Pattern, Key, Location
        self.Screen = Screen
        self.Pattern = Pattern
        self.Location = Location

        self.Key = Key
        self.is_reply = 0
        self.lock = threading.Lock()
        self.current_date = None
        self.today_counter = 0

        # 创建 Screen 对象
        self.screen = Screen()

        # 定义图像路径
        self.drag_start = os.path.join(PROJECT_ROOT, "lib", "sikulix", "wechat", "drag_start.png")
        self.drag_end = os.path.join(PROJECT_ROOT, "lib", "sikulix", "wechat", "drag_end.png")
        self.is_chating = os.path.join(PROJECT_ROOT, "lib", "sikulix", "wechat", "is_chating.png")
        self.isnt_replied = os.path.join(PROJECT_ROOT, "lib", "sikulix", "wechat", "isnt_replied.png")
        self.new_friend = os.path.join(PROJECT_ROOT, "lib", "sikulix", "wechat", "new_friend.png")
        self.new_friend_01 = os.path.join(PROJECT_ROOT, "lib", "sikulix", "wechat", "new_friend_01.png")
        self.new_friend_accept = os.path.join(PROJECT_ROOT, "lib", "sikulix", "wechat", "new_friend_accept.png")
        self.new_msg_01 = os.path.join(PROJECT_ROOT, "lib", "sikulix", "wechat", "new_msg_01.png")
        self.new_msg_02 = os.path.join(PROJECT_ROOT, "lib", "sikulix", "wechat", "new_msg_02.png")
        self.replied = os.path.join(PROJECT_ROOT, "lib", "sikulix", "wechat", "replied.png")
        self.unread_msg = os.path.join(PROJECT_ROOT,"lib","sikulix","wechat","unread_msg.png")

        # 定义 Pattern 对象
        self.drag_start_pattern = self.Pattern(self.drag_start)
        self.drag_end_pattern = self.Pattern(self.drag_end)
        self.is_chating_pattern = self.Pattern(self.is_chating)
        self.isnt_replied_pattern = self.Pattern(self.isnt_replied)
        self.new_friend_pattern = self.Pattern(self.new_friend)
        self.new_friend_01_pattern = self.Pattern(self.new_friend_01)
        self.new_friend_accept_pattern = self.Pattern(self.new_friend_accept)
        self.new_msg_01_pattern = self.Pattern(self.new_msg_01)
        self.new_msg_02_pattern = self.Pattern(self.new_msg_02)
        self.replied_pattern = self.Pattern(self.replied)
        self.unread_msg_pattern = self.Pattern(self.unread_msg)

    def startup(self):
        while True:
            time.sleep(1)
            self._get_new_event()

    def _get_new_event(self):
        if self.screen.exists(self.isnt_replied_pattern) is not None:
            print("=========没回复当前消息，进行处理")
            self._handdle_message()
            if not self.is_reply:
                self._waiting_for_reply()
        if self.screen.exists(self.new_msg_01_pattern) or self.screen.exists(self.new_msg_02_pattern): # 侧边栏有新消息
            print("=========侧边栏有消息，进行处理")
            if self.screen.exists(self.new_msg_01_pattern):
                self.screen.click(self.new_msg_01_pattern)
            elif self.screen.exists(self.new_msg_02_pattern):
                self.screen.click(self.new_msg_02_pattern)
            # 在这里先检测当前聊天有没有被回复，如果没有，直接执行回复逻辑，否则检测小红点
            unread_msg_list = self.screen.findAll(self.unread_msg_pattern) # 这里反回的是迭代器，只能被读取一次
            print("=========找到所有的红点了，进行处理")
            if unread_msg_list is not None:
                for msg_processing in unread_msg_list:
                    msg_processing.click()
                    if self.screen.exists(self.is_chating_pattern) is not None: # 进入的是聊天界面
                        print("=========进去的是聊天界面，进行处理")
                        logger.debug("Already entered the chat interface.")
                        self._handdle_message()
                        if not self.is_reply:
                            self._waiting_for_reply()
                    else:
                        logger.debug("Not a chat interface, skip.")
                        continue
        elif self.screen.exists(self.new_friend_01_pattern) is not None: # 侧边栏有新的验证消息，这里插入需要不需要进行接管的判断
            self.screen.click(self.new_friend_01_pattern)
            if self.screen.exists(self.new_friend_pattern) is not None:
                self.screen.click(self.new_friend_pattern)
                verify_list = self.screen.findAll(self.new_friend_accept_pattern)
                if verify_list is not None:
                    for verify in verify_list:
                        verify.click()
                else:
                    logger.debug(f"New customer pattern but doesn't need verify?")

    def _handdle_message(self):
        with self.lock:
            self.is_reply = 0
        raw_message = self._get_history_window()
        format_message = self._get_formatted_reply_if_needed(raw_message) # 判断是否需要进行回复
        if format_message:
            sikulix_message = SikuliXMessage(format_message,False)
            logger.info(f"Message context generate: {sikulix_message}")
            context = self._compose_context(
                sikulix_message.ctype,
                str(sikulix_message.content),
                isgroup=sikulix_message.is_group,
                msg=sikulix_message,
            )

            if context:
                self.produce(context)
        else:
            with self.lock:
                self.is_reply = 1

    def _get_history_window(self):
        """从聊天窗口中拖动返回聊天记录，如果没有找到就返回None"""
        original_clipboard = pyperclip.paste()
        start_match = self.screen.find(self.drag_start_pattern)
        if start_match is not None:
            width = start_match.getW()  # 图像的宽度
            height = start_match.getH()  # 图像的高度
            self.drag_start_pattern.targetOffset(width // 2, height // 2)  # 右下角偏移
            if self.screen.exists(self.drag_end_pattern) is not None:  # 结束位置检查
                self.screen.dragDrop(self.drag_start_pattern, self.drag_end_pattern)
                self.screen.type("c", self.Key.CTRL)
                logger.debug("The selected text has been copied to the clipboard.")
                selected_text = pyperclip.paste()
                if selected_text != original_clipboard:
                    return selected_text
                else:
                    logger.debug("The pasteboard content is not updated, the text may not be selected.")
                    return None
            else:
                print("未找到结束位置")
                return None
        else:
            print("未找到起始位置")
            return None

    def _send_reply(self, text: str, reply:ReplyType):
        """发送AI返回的消息到前端目标

        Args:
            context: 包含全部消息信息的消息类
            reply: AI生成的回复
        """
        reply_text = reply.content
        logger.info(f"Ready to reply: {reply_text}")
        if "<end>" in reply_text:
            pass
        reply_list = re.findall(r'「(.*?)」', reply_text)
        for content in reply_list:
            pyperclip.copy(content)
            logger.debug("Text copied to clipboard.")
            if self.screen.exists(self.is_chating) is not None:
                self.screen.click(self.is_chating)
                self.screen.type("v", self.Key.CTRL)
                self.screen.type("\n")
                with self.lock:
                    self.is_reply = 1
                time.sleep(2) # 这是同步各方面参数的，因为用的是模拟按键的方式，所以操作和数据之间会有时间差，用这个sleep来抹平时间差

    def _get_formatted_reply_if_needed(self,message):
        if message == None: # 如果复制内容为空
            return None
        lines = message.strip().split("\n")
        your_wx_name = conf().get("wx_name") + ":"
        if len(lines) <= 2: # 如果复制只有客户发送的一句消息，那么消息直接复制出来的是文本
            return f"""用户: \n{message}"""
        if your_wx_name not in lines[-2]: # 最后一句是自己回复的
            return None
        return message

    def send(self, reply: Reply, context: Context):
        receiver = context["receiver"]
        if reply.type in [ReplyType.TEXT, ReplyType.ERROR, ReplyType.INFO]:
            reply_text = reply.content
            self._send_reply(reply_text)
            logger.info("Do send text to {}: {}".format(receiver, reply_text))
        else:
            logger.debug("Repily type error.")

    def _waiting_for_reply(self, timeout=60):
        start_time = time.time()
        while True:
            with self.lock:
                if self.is_reply == 1:
                    break
            if time.time() - start_time > timeout:
                break
            time.sleep(1)

    def shutdown(self):
        jpype.shutdownJVM()



if __name__ == "__main__":
    jvm_path = r"C:\Program Files\Java\jdk-23\bin\server\jvm.dll"
    sikulix_jar_path = r"D:\Program\dify-on-wechat\lib\sikulix\sikulixide-2.0.5-win.jar"

    automation = SikuliXChannel(jvm_path, sikulix_jar_path)
    automation._get_history_window()
    automation.shutdown()