from plugins import *
from common import const
from channel import channel_factory
from config import load_config, save_config, conf
import requests

# 加载配置
#load_config()


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

        return nickname, avatar_url
    except Exception as e:
        logger.error(f"获取Gewechat用户信息失败: {str(e)}")
        return None, None


def gewe_log_out():
    """gewe退出登陆"""
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

        logout_status = client.log_out(app_id)
        if not logout_status:
            return False, "退出登陆失败"
        if logout_status.get('msg') == "操作成功":
            return True, "操作成功"

        return None, None
    except Exception as e:
        logger.error(f"登出失败: {str(e)}")
        return None, None


def get_qrcode_url():
    try:
        from lib.gewechat.client import GewechatClient
        base_url = conf().get("gewechat_base_url")
        token = conf().get("gewechat_token")
        app_id = conf().get("gewechat_app_id")
        client = GewechatClient(base_url, token)

        client.login(app_id)
        from lib.gewechat.util.terminal_printer import url
        print(url)
        return url
    except Exception as e:
        logger.error(f"获取二维码失败: {str(e)}")
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


if __name__ == "__main__":
    url = get_qrcode_url()
    print(url)