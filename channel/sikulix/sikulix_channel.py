import os
import re
import sys
import time
import jpype
import datetime
import threading
import pyperclip
import jpype.imports
from common.log import logger
from bridge.context import Context
from core.data.watch_dog import data
from bridge.reply import Reply, ReplyType
from channel.chat_channel import ChatChannel
from channel.sikulix.sikulix_message import SikuliXMessage

class SikuliXChannel(ChatChannel):
    def __init__(self):
        # 启动 JVM，并加载 sikulixapi.jar

        if getattr(sys, 'frozen', False):
            # 打包后的环境
            PROJECT_ROOT = os.path.dirname(sys.executable)
        else:
            # 开发环境
            PROJECT_ROOT = os.path.dirname(os.path.abspath(sys.argv[0]))
        #self.jvm_path = jpype.getDefaultJVMPath()
        self.jvm_path = r"C:\Program Files\Java\jdk-23\bin\server\jvm.dll"
        #self.sikulix_jar_path = os.path.join(PROJECT_ROOT,"lib","sikulix","sikulixide-2.0.5-win.jar")
        self.sikulix_jar_path = r"D:\Program\WangLongAI-1\lib\sikulix\sikulixide-2.0.5-win.jar"
        logger.info(f"JVM path: {self.jvm_path}, sikulix_jar_path:{self.sikulix_jar_path}")
        super().__init__()
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
        self.new_msg = os.path.join(PROJECT_ROOT,"lib","sikulix","wecom","new-msg.png")#r"D:\Program\dify-on-wechat\lib\sikulix\wecom\new-msg.png"
        self.need_verify = os.path.join(PROJECT_ROOT,"lib","sikulix","wecom","need-verify.png")#r"D:\Program\dify-on-wechat\lib\sikulix\wecom\need-verify.png"
        self.new_customer = os.path.join(PROJECT_ROOT,"lib","sikulix","wecom","new-customer.png")#r"D:\Program\dify-on-wechat\lib\sikulix\wecom\new-customer.png"
        self.waitfor_verify_01 = os.path.join(PROJECT_ROOT,"lib","sikulix","wecom","waitfor-verify-01.png")#r"D:\Program\dify-on-wechat\lib\sikulix\wecom\waitfor-verify-01.png"
        self.be_verify = os.path.join(PROJECT_ROOT,"lib","sikulix","wecom","be-verify.png")#r"D:\Program\dify-on-wechat\lib\sikulix\wecom\be-verify.png"
        self.unread_msg = os.path.join(PROJECT_ROOT,"lib","sikulix","wecom","unread-msg.png")#r"D:\Program\dify-on-wechat\lib\sikulix\wecom\unread-msg.png"
        self.is_chating = os.path.join(PROJECT_ROOT,"lib","sikulix","wecom","is-chating.png")#r"D:\Program\dify-on-wechat\lib\sikulix\wecom\is-chating.png"
        self.drag_top = os.path.join(PROJECT_ROOT,"lib","sikulix","wecom","drag_top.png")#r"D:\Program\dify-on-wechat\lib\sikulix\wecom\drag_top.png"
        self.drag_bottom = os.path.join(PROJECT_ROOT,"lib","sikulix","wecom","drag_bottom.png")#r"D:\Program\dify-on-wechat\lib\sikulix\wecom\drag_bottom.png"
        self.isnt_replied = os.path.join(PROJECT_ROOT,"lib","sikulix","wecom","isnt_replied.png")#r"D:\Program\dify-on-wechat\lib\sikulix\wecom\isnt_replied.png"
        self.customer_info = os.path.join(PROJECT_ROOT,"lib","sikulix","wecom","customer_info.png")#r"D:\Program\dify-on-wechat\lib\sikulix\wecom\customer_info.png"
        self.set_remark = os.path.join(PROJECT_ROOT,"lib","sikulix","wecom","set_remark.png")#r"D:\Program\dify-on-wechat\lib\sikulix\wecom\set_remark.png"
        self.remark_success = os.path.join(PROJECT_ROOT,"lib","sikulix","wecom","remark_success.png")#r"D:\Program\dify-on-wechat\lib\sikulix\wecom\remark_success.png"

        # 定义 Pattern 对象
        self.new_msg_pattern = self.Pattern(self.new_msg).similar(0.8)
        self.unread_msg_pattern = self.Pattern(self.unread_msg).similar(0.8)
        self.need_verify_pattern = self.Pattern(self.need_verify).similar(0.8)
        self.new_customer_pattern = self.Pattern(self.new_customer).similar(0.8)
        self.waitfor_verify_pattern = self.Pattern(self.waitfor_verify_01)
        self.be_verify_pattern = self.Pattern(self.be_verify)
        self.is_chating_pattern = self.Pattern(self.is_chating)
        self.strat_pattern = self.Pattern(self.drag_top).similar(0.8)
        self.end_pattern = self.Pattern(self.drag_bottom).similar(0.9)
        self.isnt_replied_pattern = self.Pattern(self.isnt_replied).similar(0.8)
        self.customer_info_pattern = self.Pattern(self.customer_info).similar(0.8)
        self.set_remark_pattern = self.Pattern(self.set_remark)
        self.remark_success_pattern = self.Pattern(self.remark_success)

    def startup(self):
        while True:
            time.sleep(1)
            self._get_new_event()

    def _get_new_event(self):
        if self.screen.exists(self.isnt_replied_pattern) is not None:
            self._handdle_message()
            if not self.is_reply:
                self._waiting_for_reply()
        if self.screen.exists(self.new_msg_pattern) is not None: # 侧边栏有新消息
            self.screen.click(self.new_msg_pattern)
            # 在这里先检测当前聊天有没有被回复，如果没有，直接执行回复逻辑，否则检测小红点
            unread_msg_list = self.screen.findAll(self.unread_msg_pattern) # 这里反回的是迭代器，只能被读取一次
            if unread_msg_list is not None:
                for msg_processing in unread_msg_list:
                    msg_processing.click()
                    if self.screen.exists(self.is_chating_pattern) is not None: # 进入的是聊天界面
                        logger.debug("Already entered the chat interface.")
                        self._handdle_message()
                        if not self.is_reply:
                            self._waiting_for_reply()
                    else:
                        logger.debug("Not a chat interface, skip.")
                        continue
        elif self.screen.exists(self.need_verify_pattern) is not None: # 侧边栏有新的验证消息，这里插入需要不需要进行接管的判断
            self.screen.click(self.need_verify_pattern)
            if self.screen.exists(self.new_customer_pattern) is not None:
                self.screen.click(self.new_customer_pattern)
                verify_list = self.screen.findAll(self.waitfor_verify_pattern)
                if verify_list is not None:
                    for verify in verify_list:
                        verify.click()
                        if self.screen.exists(self.be_verify_pattern) is not None:
                            logger.debug("Customer addition request detected, processing in progress.")
                            self.screen.click(self.be_verify_pattern)
                        else:
                            pass
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
        start_match = self.screen.find(self.strat_pattern)
        if start_match is not None:
            width = start_match.getW()  # 图像的宽度
            height = start_match.getH()  # 图像的高度
            self.strat_pattern.targetOffset(width // 2, height // 2)  # 右下角偏移
            if self.screen.exists(self.end_pattern) is not None:  # 结束位置检查
                self.screen.dragDrop(self.strat_pattern, self.end_pattern)
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
            self.rename_customer()
            data().update_stat("ended_conversations")
        reply_list = re.findall(r'「(.*?)」', reply_text)
        data().update_stat("reply_count") if reply_list else None
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

    def rename_customer(self):
        """重命名事件，需要原来的名字作为参数"""
        match = self.screen.exists(self.customer_info_pattern)
        if match is not None:
            width, height = match.getW(), match.getH()
            click_x = match.getX() + width
            click_y = match.getY() + height // 2
            location = self.Location(click_x, click_y)
            self.screen.click(location)
            if self.screen.exists(self.set_remark_pattern) is not None:
                self.screen.click(self.set_remark_pattern)
                name_remark = self._generate_name_remark()
                pyperclip.copy(name_remark)
                self.screen.type("a", self.Key.CTRL)
                self.screen.type(self.Key.LEFT)
                self.screen.type("v", self.Key.CTRL)
                if self.screen.exists(self.remark_success_pattern) is not None:
                    self.screen.click(self.remark_success_pattern)

    def _generate_name_remark(self):
        """生成[20250220-01-何颂生]这样的重命名文本"""
        today = datetime.datetime.now().strftime("%m.%d")
        if self.current_date != today:
            self.current_date = today
            self.today_counter = 0
        self.today_counter += 1
        formatted_counter = f"{self.today_counter:02d}"
        remark = f"{self.current_date}-{formatted_counter}-留资"
        return remark

    def _get_formatted_reply_if_needed(self,message):
        if message == None: # 如果复制内容为空
            return None
        lines = message.strip().split("\n")
        if len(lines) <= 2: # 如果复制只有客户发送的一句消息，那么消息直接复制出来的是文本
            return f"""客户@微信 2/20 20:23:57\n{message}"""
        if "@" not in lines[-2]: # 最后一句是自己回复的
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