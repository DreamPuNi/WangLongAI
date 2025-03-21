import io
import re
import sys
import time
import uuid
import jpype
import ntwork
import random
import tempfile
import requests
import threading
import pyperclip
import jpype.imports
from PIL import Image
from queue import Queue
from bridge.reply import *
from bridge.context import *
from channel.wecommix import run
from common.singleton import singleton
from channel.wecommix.run import wework
from common.time_check import time_checker
from channel.chat_channel import ChatChannel
from channel.wecommix.wecommix_message import *
from common.utils import compress_imgfile, fsize
from config import conf,save_config, get_broadcast_config, load_config
from channel.wecommix.wecommix_message import WecomMixMessage
from apscheduler.schedulers.background import BackgroundScheduler

ntwork.set_wework_exe_path(wework_version='4.0.8.6027')
os.environ['ntwork_LOG'] = "ERROR"

def get_wxid_by_name(room_members, group_wxid, name):
    """
    从群聊中获取指定用户的wxid

    Args:
        room_members: 群聊信息
        group_wxid: 群聊的wxid
        name: 用户的昵称或用户名

    Returns:
        return: 用户的wxid
    """
    if group_wxid in room_members:
        for member in room_members[group_wxid]['member_list']:
            if member['room_nickname'] == name or member['username'] == name:
                return member['user_id']
    return None  # 如果没有找到对应的group_wxid或name，则返回None

def download_and_compress_image(url, filename, quality=30):
    """
    下载并且压缩图片

    Args:
        url: 图片的url
        filename: 图片的文件名
        quality: 图片的质量

    Returns:
        image_path: 图片的路径
    """
    directory = os.path.join(os.getcwd(), "tmp")
    if not os.path.exists(directory):
        os.makedirs(directory)

    pic_res = requests.get(url, stream=True)
    image_storage = io.BytesIO()
    for block in pic_res.iter_content(1024):
        image_storage.write(block)
    # 检查图片大小并可能进行压缩
    sz = fsize(image_storage)
    if sz >= 10 * 1024 * 1024:  # 如果图片大于 10 MB
        logger.info("[wework] image too large, ready to compress, sz={}".format(sz))
        image_storage = compress_imgfile(image_storage, 10 * 1024 * 1024 - 1)
        logger.info("[wework] image compressed, sz={}".format(fsize(image_storage)))
    # 将内存缓冲区的指针重置到起始位置
    image_storage.seek(0)
    # 读取并保存图片
    image = Image.open(image_storage)
    image_path = os.path.join(directory, f"{filename}.png")
    image.save(image_path, "png")

    return image_path

def download_video(url, filename):
    """
    下载视频

    Args:
        url: 视频的url
        filename: 视频的文件名

    Returns:
        video_path: 视频的路径
    """
    # 确定保存视频的目录
    directory = os.path.join(os.getcwd(), "tmp")
    # 如果目录不存在，则创建目录
    if not os.path.exists(directory):
        os.makedirs(directory)

    # 下载视频
    response = requests.get(url, stream=True)
    total_size = 0

    video_path = os.path.join(directory, f"{filename}.mp4")

    with open(video_path, 'wb') as f:
        for block in response.iter_content(1024):
            total_size += len(block)

            # 如果视频的总大小超过30MB (30 * 1024 * 1024 bytes)，则停止下载并返回
            if total_size > 30 * 1024 * 1024:
                logger.info("[WX] Video is larger than 30MB, skipping...")
                return None

            f.write(block)

    return video_path

def create_message(wework_instance, message, is_group):
    """
    将收到的消息格式化为 WeworkMessage 对象

    Args:
        wework_instance: Wework 实例
        message: 收到的消息
        is_group: 是否为群聊

    Returns:
        cmsg: WeworkMessage 对象
    """
    logger.debug(f"正在为{'群聊' if is_group else '单聊'}创建 WecommixMessage")
    cmsg = WecomMixMessage(message, wework=wework_instance, is_group=is_group)
    logger.debug(f"cmsg:{cmsg}")
    return cmsg

def handle_message(cmsg, is_group):
    """
    根据是否群聊选择对应的处理函数

    Args:
        cmsg: WecommixMessage 对象
        is_group: 是否为群聊
    """
    logger.debug(f"准备用 WecommixChannel 处理{'群聊' if is_group else '单聊'}消息")
    if is_group:
        WecomMixChannel().handle_group(cmsg)
    else:
        WecomMixChannel().handle_single(cmsg)
    logger.debug(f"已用 WecommixChannel 处理完{'群聊' if is_group else '单聊'}消息")

def _check(func):
    """检查如果传入的消息超时一分钟了就不再调用func处理，这个用修饰器的方法调用"""
    def wrapper(self, cmsg: ChatMessage):
        msgId = cmsg.msg_id
        create_time = cmsg.create_time  # 消息时间戳
        if create_time is None:
            return func(self, cmsg)
        if int(create_time) < int(time.time()) - 60:  # 跳过1分钟前的历史消息
            logger.debug("[WX]history message {} skipped".format(msgId))
            return
        return func(self, cmsg)

    return wrapper

@wework.msg_register( # 当接收到以下消息类型时调用all_msg_handle函数
    [ntwork.MT_RECV_TEXT_MSG, ntwork.MT_RECV_IMAGE_MSG, 11072, ntwork.MT_RECV_LINK_CARD_MSG,ntwork.MT_RECV_FILE_MSG, ntwork.MT_RECV_VOICE_MSG])
def all_msg_handler(wework_instance: ntwork.WeWork, message):
    """处理所有消息"""
    logger.debug(f"收到消息: {message}")
    if WecomMixChannel().inited and 'data' in message:
        sender = message['data'].get("sender", None)
        if sender and sender == WecomMixChannel().user_id:
            logger.debug("自己发的，直接结束")
            return
        # 首先查找conversation_id，如果没有找到，则查找room_conversation_id
        conversation_id = message['data'].get('conversation_id', message['data'].get('room_conversation_id'))

        if conversation_id is not None:
            is_group = "R:" in conversation_id
            try:
                cmsg = create_message(wework_instance=wework_instance, message=message, is_group=is_group)
            except NotImplementedError as e:
                logger.error(f"[WX]{message.get('MsgId', 'unknown')} 跳过: {e}")
                return None
            delay = random.randint(1, 2)
            timer = threading.Timer(delay, handle_message, args=(cmsg, is_group))
            timer.start()
        else:
            logger.debug("消息数据中无 conversation_id")
            return None
    return None

def accept_friend_with_retries(wework_instance, user_id, corp_id):
    """接受好友请求"""
    result = wework_instance.accept_friend(user_id, corp_id)
    logger.debug(f'result:{result}')

def get_with_retry(get_func, max_retries=3, delay=5):
    """重试获取数据的func"""
    retries = 0
    result = None
    while retries < max_retries:
        result = get_func()
        if result:
            break
        logger.warning(f"获取数据失败，重试第{retries + 1}次······")
        retries += 1
        time.sleep(delay)  # 等待一段时间后重试
    return result

@singleton
class WecomMixChannel(ChatChannel):
    NOT_SUPPORT_REPLYTYPE = []

    def __init__(self):
        super().__init__()
        self.inited = False
        self.remark_queue = Queue()
        self.sikulix_thread = None

    def startup(self):
        smart = True # 因为是混合模式，所以不支持多开，因为通过图像判断操作那个企微太麻烦了，代码耦合性过高
        wework.open(smart)
        logger.info("等待登陆企业微信")
        wework.wait_login()
        login_info = wework.get_login_info()
        self.user_id = login_info['user_id']
        self.name = login_info['nickname'] if login_info['nickname'] else login_info['username']
        logger.info(f"登录信息:>>>user_id:{self.user_id}>>>>>>>>name:{self.name}")
        logger.info("静默延迟30s，等待客户端刷新数据，请勿进行任何操作······")
        time.sleep(30)
        self.contacts = get_with_retry(wework.get_external_contacts) # 这里是获取的企微的外部联系人
        rooms = get_with_retry(wework.get_rooms) # 这里是获取的群聊
        directory = os.path.join(os.getcwd(), "tmp")
        if not self.contacts or not rooms:
            logger.error("获取contacts或rooms失败，程序退出")
            ntwork.exit_()
            os.exit(0)
        if not os.path.exists(directory): # 这里把获取的联系人列表直接保存了
            os.makedirs(directory)
        with open(os.path.join(directory, 'wework_contacts.json'), 'w', encoding='utf-8') as f:
            json.dump(self.contacts, f, ensure_ascii=False, indent=4)
        with open(os.path.join(directory, 'wework_rooms.json'), 'w', encoding='utf-8') as f:
            json.dump(rooms, f, ensure_ascii=False, indent=4)
        result = {}
        for room in rooms['room_list']:
            room_wxid = room['conversation_id'] # 获取聊天室ID
            room_members = wework.get_room_members(room_wxid) # 获取聊天室成员
            result[room_wxid] = room_members # 将聊天室成员保存到结果字典中
        with open(os.path.join(directory, 'wework_room_members.json'), 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        logger.info("wework程序初始化完成········")
        self.inited = True
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(self.schedule_broadcast, 'interval', minutes=1)
        self.scheduler.start()
        self.sikulix_thread = SikuliXWorker(self.remark_queue)
        self.sikulix_thread.daemon = True
        self.sikulix_thread.start()
        run.forever()

    @time_checker
    @_check
    def handle_single(self, cmsg: ChatMessage):
        if cmsg.from_user_id == cmsg.to_user_id: # ignore self reply
            return
        # print("cmsg.from_user_nickname:",cmsg.from_user_nickname)
        user_marker = self.find_remarkname_by_coverid(cmsg.other_user_id)
        if conf().get("skip_ai_keywords") is not None:
            if conf().get("skip_ai_keywords") in user_marker:
                logger.info("检测到人工关键词:{},跳过回复".format(user_marker))
                return
        if cmsg.ctype == ContextType.VOICE:
            if not conf().get("speech_recognition"):
                return
            logger.debug("[Wecommix]receive voice msg: {}".format(cmsg.content))
        elif cmsg.ctype == ContextType.IMAGE:
            logger.debug("[Wecommix]receive image msg: {}".format(cmsg.content))
        elif cmsg.ctype == ContextType.PATPAT:
            logger.debug("[Wecommix]receive patpat msg: {}".format(cmsg.content))
        elif cmsg.ctype == ContextType.TEXT:
            logger.debug("[Wecommix]receive text msg: {}, cmsg={}".format(json.dumps(cmsg._rawmsg, ensure_ascii=False), cmsg))
        else:
            logger.debug("[Wecommix]receive msg: {}, cmsg={}".format(cmsg.content, cmsg))
        context = self._compose_context(cmsg.ctype, cmsg.content, isgroup=False, msg=cmsg)
        if context:
            self.produce(context)

    @time_checker
    @_check
    def handle_group(self, cmsg: ChatMessage):
        if cmsg.ctype == ContextType.VOICE:
            if not conf().get("speech_recognition"):
                return
            logger.debug("[WX]receive voice for group msg: {}".format(cmsg.content))
        elif cmsg.ctype == ContextType.IMAGE:
            logger.debug("[WX]receive image for group msg: {}".format(cmsg.content))
        elif cmsg.ctype in [ContextType.JOIN_GROUP, ContextType.PATPAT]:
            logger.debug("[WX]receive note msg: {}".format(cmsg.content))
        elif cmsg.ctype == ContextType.TEXT:
            pass
        else:
            logger.debug("[WX]receive group msg: {}".format(cmsg.content))
        context = self._compose_context(cmsg.ctype, cmsg.content, isgroup=True, msg=cmsg)
        if context:
            self.produce(context)

    def send(self, reply: Reply, context: Context):
        from core.data.watch_dog import data
        logger.debug(f"context: {context}")
        receiver = context["receiver"]
        actual_user_id = context["msg"].actual_user_id
        if reply.type == ReplyType.TEXT or reply.type == ReplyType.TEXT_:
            match = re.search(r"^@(.*?)\n", reply.content)
            logger.debug(f"match: {match}")
            # ==================>   在这里添加过滤器   <==================
            if match:
                new_content = re.sub(r"^@(.*?)\n", "\n", reply.content)
                at_list = [actual_user_id]
                logger.debug(f"new_content: {new_content}")
                wework.send_room_at_msg(receiver, new_content, at_list)
                # 这里带@的先不管
            else:
                nick_name = self.find_nickname_by_coverid(receiver)
                conf().user_datas[receiver]['history'].append({ "assistant": reply.content})
                if "<end>" in reply.content:  # 先判断是不是对话结束,如果是就转人工
                    data().update_stat("ended_conversations")
                    logger.info(f"{nick_name}:{receiver}对话结束，转人工")
                    self.add_remark_task(user_nickname=nick_name,status="end")
                    # self.send_transfer_notice(receiver, user)  # 执行通知函数
                reply_list = re.findall(r'「(.*?)」', reply.content, re.DOTALL)
                data().update_stat("reply_count") if reply_list else None
                for content in reply_list:
                    time.sleep(1)
                    wework.send_text(receiver, content)
            # ==================>   在这里添加过滤器   <==================
            logger.info("[WX] sendMsg={}, receiver={}".format(reply, receiver))
        elif reply.type == ReplyType.ERROR or reply.type == ReplyType.INFO:
            wework.send_text(receiver, reply.content)
            logger.info("[WX] sendMsg={}, receiver={}".format(reply, receiver))
        elif reply.type == ReplyType.IMAGE:  # 从文件读取图片
            image_storage = reply.content
            image_storage.seek(0)
            # Read data from image_storage
            data = image_storage.read()
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp:
                temp_path = temp.name
                temp.write(data)
            # Send the image
            wework.send_image(receiver, temp_path)
            # wework.send_image(receiver, r"C:\Users\龙崎盈子\Desktop\CurrentProcessing\doc\doc\表情包\哭哭.gif")
            logger.info(f"[WX] sendImage, receiver={receiver}/temp_path={temp_path}")
            # Remove the temporary file
            # os.remove(temp_path)
        elif reply.type == ReplyType.IMAGE_URL:  # 从网络下载图片
            img_url = reply.content
            filename = str(uuid.uuid4())

            # 调用你的函数，下载图片并保存为本地文件
            image_path = download_and_compress_image(img_url, filename)

            wework.send_image(receiver, file_path=image_path)
            logger.info("[WX] sendImage url={}, receiver={}".format(img_url, receiver))
        elif reply.type == ReplyType.VIDEO_URL:
            video_url = reply.content
            filename = str(uuid.uuid4())
            video_path = download_video(video_url, filename)

            if video_path is None:
                # 如果视频太大，下载可能会被跳过，此时 video_path 将为 None
                wework.send_text(receiver, "抱歉，视频太大了！！！")
            else:
                wework.send_video(receiver, video_path)
            logger.info("[WX] sendVideo, receiver={}".format(receiver))
        elif reply.type == ReplyType.VOICE:
            current_dir = os.getcwd()
            voice_file = reply.content.split("/")[-1]
            reply.content = os.path.join(current_dir, "tmp", voice_file)
            wework.send_file(receiver, reply.content)
            logger.info("[WX] sendFile={}, receiver={}".format(reply.content, receiver))

    def update_contacts(self):
        logger.debug("Update external contacts.")
        self.contacts = get_with_retry(wework.get_external_contacts)

    def add_remark_task(self,user_nickname, status):
        """添加备注任务"""
        message = {
            "user_nickname": user_nickname,
            "status": status
        }
        self.remark_queue.put(message)
        logger.info(f"添加备注任务: {message}")

    def schedule_broadcast(self):
        """
        定时群发事件

        Args:
            直接在setting.json中配置定时任务，图片的话<img>图片地址</img>
        """
        if not conf().get("wecommix_broadcast"):
            return
        if not self.inited:
            logger.error("企业微信未初始化或联系人未获取")
            return
        try:
            self.contacts = get_with_retry(wework.get_external_contacts)
        except Exception as e:
            logger.error("获取联系人失败: {}".format(e))

        broadcast_config = get_broadcast_config()

        now_time = datetime.datetime.now().strftime("%H:%M")
        for entry in broadcast_config:
            if entry['time'] != now_time:
                continue
            logger.info(f"开始{now_time}的群发事件")
            include = entry['filter_by_remark']['include']
            exclude = entry['filter_by_remark']['exclude']
            messages = entry['msg_list']
            filtered_contacts = []
            for contact in self.contacts.get("user_list",[]):
                remark = contact.get("remark","")
                if (not include or include in remark) and (not exclude or exclude not in remark):
                    filtered_contacts.append(contact)
            logger.debug("筛选后的联系人: {}".format(filtered_contacts))

            for contact in filtered_contacts:
                conversation_id = contact["conversation_id"]
                remark_name = contact["remark"]
                for msg in messages:
                    try:
                        if "<img>" in msg:
                            img_path = msg[len("<img>"):-len("</img>")]
                            logger.debug(f"发送图片{img_path}至{remark_name}成功")
                            wework.send_image(conversation_id, img_path)
                            time.sleep(1)
                        wework.send_text(conversation_id,msg)
                        logger.debug(f"发送消息{msg}至{remark_name}成功")
                        time.sleep(1)
                    except Exception as e:
                        logger.error(f"发送消息{msg}至{remark_name}失败: {e}")

    def find_nickname_by_coverid(self,conversation_id):
        """用对话ID找到其对应的昵称"""
        for contact in self.contacts.get("user_list",[]):
            # print("current contact:",contact)
            if contact["conversation_id"] == conversation_id:
                return contact["username"]
        return None

    def find_remarkname_by_coverid(self,conversation_id):
        """用对话ID找到其对应的备注名"""
        for contact in self.contacts.get("user_list",[]):
            # print("current contact:",contact)
            if contact["conversation_id"] == conversation_id:
                return contact["remark"]
        return "未知用户"# 这意味着为啥没有保存这个用户的信息

class SikuliXWorker(threading.Thread):
    def __init__(self, task_queue):

        if getattr(sys, 'frozen', False):
            PROJECT_ROOT = os.path.dirname(sys.executable)
        else:
            PROJECT_ROOT = os.path.dirname(os.path.abspath(sys.argv[0]))
        # self.jvm_path = jpype.getDefaultJVMPath()
        self.jvm_path = r"C:\Program Files\Java\jdk-23\bin\server\jvm.dll"
        self.sikulix_jar_path = os.path.join(PROJECT_ROOT,"lib","sikulix","sikulixide-2.0.5-win.jar")
        # self.sikulix_jar_path = r"D:\Program\WangLongAI\lib\sikulix\sikulixide-2.0.5-win.jar"
        logger.info(f"JVM path: {self.jvm_path}, sikulix_jar_path:{self.sikulix_jar_path}")

        super().__init__()
        jpype.startJVM(self.jvm_path, classpath=[self.sikulix_jar_path])
        from org.sikuli.script import Screen, Pattern, Key, Location
        self.Screen = Screen
        self.Pattern = Pattern
        self.Location = Location

        # 创建Screen对象
        self.screen = Screen()
        # 图像路径
        self.need_verify = os.path.join(PROJECT_ROOT, "lib", "sikulix", "wecommix", "need-verify.png")
        self.new_customer = os.path.join(PROJECT_ROOT, "lib", "sikulix", "wecommix", "new-customer.png")
        self.be_verify = os.path.join(PROJECT_ROOT, "lib", "sikulix", "wecommix", "be-verify.png")
        self.finish_verify = os.path.join(PROJECT_ROOT, "lib", "sikulix", "wecommix", "finish-verify.png")
        self.search_box = os.path.join(PROJECT_ROOT, "lib", "sikulix", "wecommix", "search-box.png")
        self.msg_moreinfo = os.path.join(PROJECT_ROOT, "lib", "sikulix", "wecommix", "msg-moreinfo.png")
        self.set_remark = os.path.join(PROJECT_ROOT, "lib", "sikulix", "wecommix", "msg-setremark.png")
        self.cancer_search = os.path.join(PROJECT_ROOT, "lib", "sikulix", "wecommix", "cancer-search.png")
        # Pattern对象
        self.need_verify_pattern = self.Pattern(self.need_verify).similar(0.8)
        self.new_customer_pattern = self.Pattern(self.new_customer).similar(0.8)
        self.be_verify_pattern = self.Pattern(self.be_verify)
        self.finish_verify_pattern = self.Pattern(self.finish_verify)
        self.search_box_pattern = self.Pattern(self.search_box).similar(0.9)
        self.msg_moreinfo_pattern = self.Pattern(self.msg_moreinfo)
        self.set_remark_pattern = self.Pattern(self.set_remark)
        self.cancer_search_pattern = self.Pattern(self.cancer_search)

        self.daemon = True
        self.running = True
        self.task_queue = task_queue
        self.current_date = None
        self.today_counter = 0
        self.Key = Key

    def run(self):
        logger.info("SikuliXWorker 线程已启动！")
        while self.running:
            try:
                if not self.task_queue.empty():
                    raw_data = self.task_queue.get()
                    user_nickname = raw_data.get("user_nickname")
                    status = raw_data.get("status")
                    self.update_customer_remark(user_nickname, status)
                self.handle_friend_requests()
            except Exception as e:
                logger.error(f"企业微信SikuliXWorker出现异常: {e}")
                time.sleep(3)

    def handle_friend_requests(self):
        """处理好友请求"""
        if self.screen.exists(self.need_verify_pattern) is not None:
            self.screen.click(self.need_verify_pattern)
            match = self.screen.exists(self.new_customer_pattern)
            if match is not None:
                self.screen.click(self.new_customer_pattern)
                width, height = match.getW(), match.getH()
                click_x = match.getX() + width * 4
                click_y = match.getY() + height // 2
                location = self.Location(click_x, click_y)
                self.screen.click(location)
                while self.screen.exists(self.be_verify_pattern):
                    self.screen.click(self.be_verify_pattern)
                    self.screen.click(self.finish_verify_pattern)
                    self.screen.type(self.Key.DOWN)
                    time.sleep(3)
            else:
                logger.debug(f"New customer pattern but doesn't need verify?")

    def update_customer_remark(self, nick_name, status):
        """更新客户备注"""
        # print("ckp-03")
        if self.screen.exists(self.search_box_pattern) is not None:
            self.screen.click(self.search_box_pattern)
            # print("ckp-04")
            pyperclip.copy(nick_name)
            time.sleep(0.5)
            self.screen.type("v", self.Key.CTRL)
            logger.info("Rename the customer to {}".format(nick_name))
            if self.screen.exists(self.msg_moreinfo_pattern) is not None:
                self.screen.click(self.msg_moreinfo_pattern)
            if self.screen.exists(self.set_remark_pattern):
                self.screen.click(self.set_remark_pattern)
                time.sleep(0.5)
                self.screen.type(self.Key.HOME)
                prefix = self._generate_name_remark()
                pyperclip.copy(prefix)
                self.screen.type("v", self.Key.CTRL)
                time.sleep(0.5)
                self.screen.type("\n")
        # 添加清除搜索框和点击空白
        match = self.screen.exists(self.cancer_search_pattern)
        if match:
            self.screen.click(self.cancer_search_pattern)
            width, height = match.getW(), match.getH()
            click_x = match.getX() + width
            click_y = match.getY() - height // 2
            location = self.Location(click_x, click_y)
            self.screen.click(location)


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







