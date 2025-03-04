from plugins import *
from common import const
from channel import channel_factory
from config import load_config, save_config, conf
import requests

# 加载配置
load_config()
current_process_instance = None

def on_channel_change(selected_value):
    conf().set("channel_type", selected_value)
    save_config()
    return f"你选择了客户端: {selected_value}"


def update_config(key, value):
    conf().set(key, value)
    save_config()


def check_gewechat_online():
    """检查gewechat用户是否在线
    Returns:
        tuple: (是否在线, 错误信息)
    """
    try:
        if conf().get("channel_type") != "gewechat":
            return False, "非gewechat，无需检查"

        base_url = conf().get("gewechat_base_url")
        token = conf().get("gewechat_token")
        app_id = conf().get("gewechat_app_id")
        if not all([base_url, token, app_id]):
            return False, "gewechat配置不完整"

        from lib.gewechat.client import GewechatClient
        client = GewechatClient(base_url, token)
        online_status = client.check_online(app_id)

        if not online_status:
            return False, "获取在线状态失败"

        if not online_status.get('data', False):
            logger.info("Gewechat用户未在线")
            return False, "用户未登录"

        return True, None

    except Exception as e:
        logger.error(f"检查gewechat在线状态失败: {str(e)}")
        return False, f"检查在线状态出错: {str(e)}"


def get_gewechat_profile():
    """获取gewechat用户信息并下载头像，仅在用户在线时返回信息"""
    try:
        is_online, error_msg = check_gewechat_online()
        if not is_online:
            logger.info(f"Gewechat状态检查: {error_msg}")
            return None, None

        from lib.gewechat.client import GewechatClient
        base_url = conf().get("gewechat_base_url")
        token = conf().get("gewechat_token")
        app_id = conf().get("gewechat_app_id")

        client = GewechatClient(base_url, token)
        profile = client.get_profile(app_id)

        if not profile or 'data' not in profile:
            return None, None

        user_info = profile['data']
        nickname = user_info.get('nickName', '未知')

        # 下载头像
        avatar_url = user_info.get('bigHeadImgUrl')
        avatar_path = None

        if avatar_url:
            try:
                avatar_path = '../../tmp/avatar.png'
                os.makedirs('../../tmp', exist_ok=True)
                response = requests.get(avatar_url)
                if response.status_code == 200:
                    with open(avatar_path, 'wb') as f:
                        f.write(response.content)
            except Exception as e:
                logger.error(f"下载头像失败: {str(e)}")
                avatar_path = None

        return nickname, avatar_path
    except Exception as e:
        logger.error(f"获取Gewechat用户信息失败: {str(e)}")
        return None, None


def start_channel(channel_name: str):
    channel = channel_factory.create_channel(channel_name)
    available_channels = [
        "wx",
        "terminal",
        "wechatmp",
        "wechatmp_service",
        "wechatcom_app",
        "wework",
        "wechatcom_service",
        "gewechat",
        "sikulix",
        const.FEISHU,
        const.DINGTALK
    ]
    if channel_name in available_channels:
        PluginManager().load_plugins()
    channel.startup()


def run():
    try:
        # load config
        load_config()
        # create channel
        channel_name = conf().get("channel_type", "wx")

        # 获取gewechat用户信息
        if channel_name == "gewechat":
            get_gewechat_profile()

        start_channel(channel_name)
    except Exception as e:
        logger.error("App startup failed!")
        logger.exception(e)


def get_qrcode_image():
    image_path = '../../tmp/login.png'
    if os.path.exists(image_path):
        return image_path
    else:
        return None


def get_avatar_image():
    image_path = '../../tmp/avatar.png'
    if os.path.exists(image_path):
        return image_path
    else:
        return None


def verify_login(username, password):
    correct_username = conf().get("web_ui_username", "dow")
    correct_password = conf().get("web_ui_password", "dify-on-wechat")
    if username == correct_username and password == correct_password:
        return True
    return False
