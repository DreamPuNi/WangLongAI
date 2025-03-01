import re
import hashlib
from config import conf
from common.log import logger
from bridge.context import ContextType
from lib.gewechat import GewechatClient
from channel.chat_message import ChatMessage

"""
由于是复制过来的消息，所以暂时不处理群聊，复制的消息体如下
望龙（ai销售版）@微信@微信联系人 2/19 14:01:46
是是是

望龙（ai销售版）@微信@微信联系人 2/19 14:01:47
是是是

张豆豆 2/19 14:04:12
让我日日

望龙（ai销售版）@微信@微信联系人 2/19 14:15:31
你能识别语音吗？

望龙（ai销售版）@微信@微信联系人 2/19 14:15:44
哎哟，不错，还是自动转换。
[{"望龙（ai销售版）":"是是是。是是是"},{"张豆豆":"让我日日"},{"望龙（ai销售版）":"你能识别语音吗？。哎哟，不错，还是自动转换。"}]
"""

class SikuliXMessage(ChatMessage):
    def __init__(self, msg, is_group=False):
        super().__init__(msg)
        self.ctype = ContextType.TEXT
        self.content,self.from_user_nickname,self.to_user_nickname = self.format_msg(msg)
        self.is_group = is_group
        self.msg_id = self.generate_msg_id(self.from_user_nickname[0])
        self.from_user_id = self.generate_msg_id(self.from_user_nickname[0])
        self.to_user_id = self.generate_msg_id(self.to_user_nickname[0])
        self.other_user_id = self.from_user_id
        self.session_id = self.from_user_id
        self.receiver = self.from_user_id

        self.other_user_nickname = self.from_user_nickname

    def format_msg(self, msg):
        """
        对消息进行格式化处理

        Args:
            msg: 直接收到的复制的消息，格式如上所述

        Return:
            result: 聊天记录，格式为：[{"望龙（ai销售版）":"是是是。是是是"},{"张豆豆":"让我日日"},{"望龙（ai销售版）":"你能识别语音吗？。哎哟，不错，还是自动转换。"}]
            list: 客服名称
        """
        # lines = msg.strip().split("\n")
        lines = [line.strip() for line in msg.strip().splitlines()]
        result = []
        current_name = None
        names_with_at = ""

        for line in lines:
            line = str(line)
            match = re.match(r"^(.+?)\s+\d{1,2}/\d{1,2}\s+\d{1,2}:\d{1,2}:\d{1,2}", line)
            if match:
                current_name = match.group(1).strip()
                if "@" in current_name:
                    current_name=(current_name.split("@")[0].strip())
                    if "@微信" in current_name:
                        current_name = current_name.replace("@微信","")
                    elif "@微信联系人" in current_name:
                        current_name = current_name.replace("@微信联系人","")
                    else:
                        pass
                    names_with_at = current_name
                elif "@" not in current_name:
                    current_name = "assistant"
            else:
                if current_name and line != '':
                    result.append({current_name: line})

        return result, names_with_at, "assistant"

    def generate_msg_id(self, name, length=20):
        """
        根据名字生成一个固定长度的 msg_id。

        Args:
            name (str): 名字（可能包含中文、英文、特殊字符或表情）。
            length (int): 生成的 msg_id 长度（默认 16，范围 10-20）。

        Returns:
            str: 生成的 msg_id。
        """
        if not (10 <= length <= 20):
            raise ValueError("length 必须在 10 到 20 之间")
        # 去除表情符号和特殊字符，只保留字母、数字、中文和常见标点符号
        filtered_name = re.sub(r"[^\w\u4e00-\u9fff\s]", "", name)
        # 将过滤后的名字转换为 UTF-8 字节序列
        byte_sequence = filtered_name.encode("utf-8")
        # 使用 MD5 哈希算法生成哈希值
        hash_object = hashlib.md5(byte_sequence)
        hash_hex = hash_object.hexdigest()  # 获取哈希值的十六进制表示
        # 截取指定长度的子字符串作为 msg_id
        msg_id = hash_hex[:length]

        return msg_id


if __name__ == "__main__":
    message = """望龙（ai销售版）@微信@微信联系人 2/19 14:01:46
是是是

望龙（ai销售版）@微信@微信联系人 2/19 14:01:47
是是是

张豆豆 2/19 14:04:12
让我日日

望龙（ai销售版）@微信@微信联系人 2/19 14:15:31
你能识别语音吗？

望龙（ai销售版）@微信@微信联系人 2/19 14:15:44
哎哟，不错，还是自动转换。"""
    sm = SikuliXMessage(message)
    print(sm)