import re
import hashlib
from config import conf
from common.log import logger
from bridge.context import ContextType
from lib.gewechat import GewechatClient
from channel.chat_message import ChatMessage

"""
由于是复制过来的消息，所以暂时不处理群聊，复制的消息体如下

硝:
[图片]

何颂生:
这是环境里面的库

何颂生:
这个安装很简单的

硝:
扫噶

何颂生:
到时候我跟你说，属于环境里面的

硝:
行

['望龙（ai销售版）:', '在吗', '', '何颂生:', '在的老板', '', '何颂生:', '你推荐了张豆豆', '', '何颂生:', '我感觉', '提示词能发挥的功能有限']
"""

class SikuliXMessage(ChatMessage):
    def __init__(self, msg, is_group=False):
        super().__init__(msg)
        self.assistant_name = "何颂生:"
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

        # self.assistant_name = conf().get("wx_name") + ":"


    def format_msg(self, msg):
        """
        对消息进行格式化处理

        Args:
            msg: 直接收到的复制的消息，格式如上所述

        Return:
            result: 聊天记录，格式为：[{"望龙（ai销售版）:":"在吗"},{"何颂生:":"在的老板。你推荐了张豆豆。我感觉\n提示词能发挥的功能有限"}]
            user_name: 用户名称
        """
        # lines = msg.strip().split("\n")
        lines = [line.strip() for line in msg.splitlines() if line.strip()]
        result = []
        current_speaker = None
        current_content = []
        user_name = ""

        for line in lines:
            if line.endswith(":"):
                if current_speaker and current_speaker != line:
                    if line == self.assistant_name:
                        result.append({current_speaker: "".join(current_content).rstrip("。")})
                        current_content = []
                    else:
                        result.append({"assistant": "".join(current_content).rstrip("。")})
                        current_content = []

                current_speaker = line
                if current_speaker != self.assistant_name:
                    user_name = current_speaker[:-1]
            else:
                current_content.append(line + "。")  # 使用句号连接

        # 处理最后一个发言者的内容
        if current_speaker:
            result.append({current_speaker: "".join(current_content).rstrip("。")})

        return result, user_name, "assistant"

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
    message = """硝:
宁夏

硝:
吴忠

何颂生:
我在陕西西安

何颂生:
听着不愿

何颂生:
远

硝:
青铜峡

硝:
[不支持类型消息]

何颂生:
okokok
不用那么详细"""
    sm = SikuliXMessage(message)
    print(sm)