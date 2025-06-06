import os
import queue
import time
import random
import signal
import asyncio
import threading
import flet as ft
from tkinter import *
from bridge.shared_queue import qr_queue
from common.log import add_log_listener
from plugins import *
from common import const
from channel import channel_factory
from multiprocessing import Process
from core.verify import VerifyAccess
from watchdog.observers import Observer
from distlib.database import make_graph
from core.flet.flet_components import grapg
from core.data.watch_dog import get_today_stats
from core.channel_infomanage.gewe_manage import *
from watchdog.events import FileSystemEventHandler
from config import conf, load_config, save_config, get_broadcast_config, save_broadcast_config


# 线程管理
current_process_instance = None

def run():
    try:
        load_config()
        channel_name = conf().get("channel_type", "wx")
        start_channel(channel_name)
    except Exception as e:
        logger.error("App startup failed!")
        logger.exception(e)

def start_channel(channel_name: str):
    channel = channel_factory.create_channel(channel_name)
    if channel_name in ["wx", "wxy", "terminal", "wechatmp", "wechatmp_service", "wechatcom_app", "wework",
                        "wechatcom_service", "gewechat", "web", const.FEISHU, const.DINGTALK]:
        PluginManager().load_plugins()

    if conf().get("use_linkai"):
        try:
            from common import linkai_client
            threading.Thread(target=linkai_client.start, args=(channel,)).start()
        except Exception as e:
            pass
    channel.startup()


# 主页面,妈了个巴子怎么这么长
def main(page: ft.Page):
    load_config()
    running=True
    page.window.center()
    page.title = "龙商学院-AI客服"
    page.window.frameless = True # 隐藏标题栏
    page.bgcolor = ft.colors.TRANSPARENT # 设置背景色为透明
    page.window.bgcolor = ft.Colors.TRANSPARENT
    page.window.width=1400 # 设置窗口大小
    page.window.height = 760
    page.padding = 0 # 移除内边距
    page.window.resizeable = False # 设置窗口不可调整大小（圆角必须）
    page.window.maximizable = False
    page.window.full_screen = False


    # ================================================
    # =================>>>路由管理部分<<<===============
    # ================================================

    def show_infocenter(e):
        infocenter_container.visible = True
        channel_container.visible = False
        model_container.visible = False
        doc_container.visible = False
        page.update()

    def show_channel(e):
        infocenter_container.visible = False
        channel_container.visible = True
        model_container.visible = False
        doc_container.visible = False

        current_value = conf().get("channel_type")
        update_parameters(
            dynamic_content=channel_dynamic_content,
            config_class="channel_type",
            e=type("MockEvent", (object,), {"control": type("MockControl", (object,), {"value": current_value})()})
        )

        page.update()

    def show_model(e):
        infocenter_container.visible = False
        channel_container.visible = False
        model_container.visible = True
        doc_container.visible = False

        current_value = conf().get("model")
        update_parameters(
            dynamic_content=model_dynamic_content,
            config_class="model",
            e=type("MockEvent", (object,), {"control": type("MockControl", (object,), {"value": current_value})()})
        )

        page.update()

    def show_doc(e):
        infocenter_container.visible = False
        channel_container.visible = False
        model_container.visible = False
        doc_container.visible = True
        page.update()

    # ================================================
    # =================>>>动态组件部分<<<===============
    # ================================================

    def minimze_to_tray(e):
        page.window.minimized = True
        page.update()

    def close_app(e):
        """这是杀掉整个窗口的代码"""
        nonlocal running
        running=False
        page.window.destroy()
        # kill_process()

    def update_parameters(dynamic_content, config_class, e):
        global current_process_instance
        current_select = e.control.value
        with open("config_grouping.json", "r", encoding="utf-8") as f:
            config_grouping = json.load(f)
        dynamic_content.controls.clear()
        scrollable_content = ft.ListView(expand=True, spacing=10, height=600)

        conf().set(config_class,current_select)

        scrollable_content.controls.append(
            ft.Text(
                value=f"{current_select}参数设置",
                size=22,
                weight=ft.FontWeight.BOLD,
                color="#000000"
            )
        )
        for arg in config_grouping[config_class][current_select]:
            scrollable_content.controls.append(
                ft.Text(
                    value=f"{config_grouping[config_class][current_select][arg]['tittle']}",
                    size=16,
                    color="#000000",
                    weight=ft.FontWeight.BOLD
                )
            )
            scrollable_content.controls.append(
                ft.Text(
                    value=f"{config_grouping[config_class][current_select][arg]['describe']}",
                    size=12,
                    color="#9B9FA1"
                )
            )
            if config_grouping[config_class][current_select][arg]['type'] == "bool":
                scrollable_content.controls.append(
                    ft.Switch(
                        label=arg,
                        value=conf().get(arg),
                        on_change=lambda e,key=arg:handle_value_change(e,key,current_select)
                    )
                )
            else:
                scrollable_content.controls.append(
                    ft.TextField(
                        label=arg,
                        value=conf().get(arg),
                        color="#000000",
                        on_change=lambda e,key=arg:handle_value_change(e,key,current_select)
                    )
                )

        def gewe_info(e):
            del scrollable_content.controls[1]

            if check_gewechat_online()[0]:
                nick_name, avatar_url = get_gewechat_profile()
                scrollable_content.controls.insert(
                    1,
                    ft.Row([
                        ft.Container(
                            content=ft.Image(src=avatar_url,width=150,height=150),
                            margin=ft.margin.only(right=40)
                        ),
                        ft.Column(
                            [
                                ft.Text(value=f"当前登陆账号：{nick_name}", size=16, color="#000000"),
                                ft.FilledButton(text="刷新状态", on_click=gewe_info),
                                ft.FilledButton(text="退出登录", on_click=lambda e: gewe_log_out())
                            ]
                        )
                    ])
                )
            else:
                qr_url = qr_queue.get(timeout=15)
                scrollable_content.controls.insert(
                    1,
                    ft.Row([
                        ft.Container(
                            content=ft.Image(src=qr_url, width=150, height=150),
                            margin=ft.margin.only(right=40)
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    value=f"请尝试扫码，如果提示二维码过期，请重新刷新状态",
                                    size=16, color="#000000"),
                                ft.FilledButton(text="刷新状态", on_click=gewe_info),
                            ]
                        )
                    ])
                )
            scrollable_content.controls.append(ft.Divider(height=15, color="#CCCCCC"))
            page.update()

        # wecommix渠道的特别设置
        if current_select == "wecommix":
            def time_picker_change(e, index,button):
                new_time = e.control.value
                if new_time:
                    broadcast_config[index]["time"] = new_time.strftime("%H:%M")
                    button.text = new_time.strftime("%H:%M")
                    button.update()

            def filter_change(e, index, key):
                broadcast_config[index]["filter_by_remark"][key] = e.control.value
                page.update()

            def msg_change(e, index, msg_index):
                msg_list = broadcast_config[index]["msg_list"]
                if msg_list[msg_index] != None:
                    broadcast_config[index]["msg_list"][msg_index] = e.control.value
                else:
                    broadcast_config[index]["msg_list"].append(e.control.value)
                page.update()

            def add_msg_field(e, index):
                message_scrollable = message_scrollables[index]
                broadcast_config[index]["msg_list"].append("")
                new_msg_index = len(broadcast_config[index]["msg_list"]) - 1
                message_scrollable.controls.insert(
                    len(message_scrollable.controls) - 1,
                    ft.TextField(
                        label="新的消息",
                        color="#000000",
                        width=600,
                        # on_change=lambda e, idx=i, msg_index=len(arg["msg_list"]): msg_change(e, idx, msg_index),
                        on_change=functools.partial(msg_change, index=index, msg_index=new_msg_index)
                    )
                )
                page.update()

            def del_msg_field(e, index):
                message_scrollable = message_scrollables[index]
                if len(message_scrollable.controls) > 2:
                    broadcast_config[index]["msg_list"].pop()
                    message_scrollable.controls.pop(-2)
                    page.update()

            def save_bdcast_config(e):
                save_broadcast_config(broadcast_config)
                logger.info(f"Save broadcast config:{broadcast_config}")
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("配置已保存！", size=16, color="#FFFFFF"),
                    bgcolor="#4CAF50",
                    duration=2000
                )
                page.snack_bar.open = True
                page.update()

            import functools
            scrollable_content.controls.append(ft.Divider(height=15, color="#CCCCCC"))
            scrollable_content.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Text(
                                value=f"群发参数设置",
                                size=22,
                                weight=ft.FontWeight.BOLD,
                                color="#000000"
                            ),
                            ft.ElevatedButton(
                                "保存群发配置",
                                bgcolor="#0079BF",
                                color="#FFFFFF",
                                width=300,
                                height=40,
                                on_click=save_bdcast_config
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    )
                )
            )

            broadcast_config = get_broadcast_config()
            message_scrollables = {}

            for i, arg in enumerate(broadcast_config):
                time_button = ft.ElevatedButton(
                    text=arg["time"],
                    # on_click=lambda _: page.open(time_picker),
                    width=100,
                    height=100,
                    bgcolor="#2196F3",
                    color="#FFFFFF",
                )
                time_picker = ft.TimePicker(
                    confirm_text="保存",
                    error_invalid_text="按理说不会报错的，但是现在报了",
                    help_text="选择发送时间",
                    on_change=functools.partial(time_picker_change, index=i, button=time_button),
                )
                
                time_button.on_click = lambda e, i=i, tp=time_picker: page.open(tp)
                message_scrollable = ft.ListView(expand=True, spacing=10)
                message_scrollables[i] = message_scrollable

                scrollable_content.controls.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                time_button,
                                ft.Column(
                                    [
                                        ft.Text(
                                            value="过滤设置",
                                            size=18,
                                            weight=ft.FontWeight.BOLD,
                                            color="#000000",
                                            width=200
                                        ),
                                        ft.TextField(
                                            label="包含此关键词的会被发送",
                                            value=arg["filter_by_remark"]["include"],
                                            color="#000000",
                                            width=200,
                                            on_change=lambda e, idx=i, key="include": filter_change(e, idx, key)
                                        ),
                                        ft.TextField(
                                            label="不包含此关键词的会被发送",
                                            value=arg["filter_by_remark"]["exclude"],
                                            color="#000000",
                                            width=200,
                                            on_change=lambda e, idx=i, key="exclude": filter_change(e, idx, key)
                                        ),
                                    ],
                                    spacing=10,
                                    alignment =ft.MainAxisAlignment.START,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(
                                            value="消息列表",
                                            size=18,
                                            weight=ft.FontWeight.BOLD,
                                            color="#000000",
                                            width=600
                                        ),
                                        ft.Container(
                                            content=message_scrollable,
                                            width=600,
                                            padding=ft.padding.all(10)
                                        )
                                    ],
                                    spacing=10,
                                    alignment=ft.MainAxisAlignment.START,
                                ),
                            ],
                            alignment = ft.MainAxisAlignment.SPACE_BETWEEN,
                            spacing=20,
                        ),
                        margin=ft.margin.only(top=15,bottom=15)
                    )
                )

                for j, msg in enumerate(arg["msg_list"]):
                    message_scrollable.controls.append(
                        ft.TextField(
                            label=f"消息{j+1}",
                            value=msg,
                            color="#000000",
                            width=600,
                            on_change=lambda e, idx=i, msg_index=j: msg_change(e, idx, msg_index)
                        )
                    )
                message_scrollable.controls.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.CupertinoFilledButton(
                                    content=ft.Text(value="添加消息",color="#FFFFFF",weight=ft.FontWeight.BOLD),
                                    opacity_on_click=0.3,
                                    on_click=lambda e, idx=i:add_msg_field(e,idx),
                                    width=285,
                                ),
                                ft.CupertinoFilledButton(
                                    content=ft.Text(value="删除最后消息",color="#FFFFFF",weight=ft.FontWeight.BOLD),
                                    opacity_on_click=0.3,
                                    on_click=lambda e, idx=i:del_msg_field(e,idx),
                                    width=285,
                                )
                            ]
                        )
                    )
                )
                scrollable_content.controls.append(ft.Divider(height=15, color="#CCCCCC"))

        if config_class == "channel_type":
            if current_select == "gewechat":
                scrollable_content.controls.insert(
                    0,
                    ft.Text(value="Gewe登录信息", size=22, weight=ft.FontWeight.BOLD, color="#000000")
                )
                if current_process_instance is None:
                    scrollable_content.controls.insert(
                        1,
                        ft.Row([
                            ft.Container(
                                content=ft.Image(
                                    src="https://longshangai.oss-cn-beijing.aliyuncs.com/software_assets/%E9%BE%99%E5%95%86-%E9%BB%91%E9%BE%99.png",
                                    width=150,
                                    height=150
                                ),
                                margin=ft.margin.only(right=40)
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        value=f"服务未运行",
                                        size=16, color="#000000"),
                                    ft.FilledButton(text="刷新状态", on_click=gewe_info),
                                ]
                            )
                        ])
                    )
                else:
                    gewe_info(e)
            scrollable_content.controls.append(ft.Divider(height=15, color="#CCCCCC"))
            scrollable_content.controls.append(
                ft.Text(value="微信公共参数设置", size=22, weight=ft.FontWeight.BOLD, color="#000000")
            )
            for arg in config_grouping[config_class]["wechat_common"]:
                scrollable_content.controls.append(
                    ft.Text(
                        value=f"{config_grouping[config_class]['wechat_common'][arg]['tittle']}",
                        size=16,
                        color="#000000",
                        weight=ft.FontWeight.BOLD)
                )
                scrollable_content.controls.append(
                    ft.Text(
                        value=f"{config_grouping[config_class]['wechat_common'][arg]['describe']}",
                        size=12,
                        color="#9B9FA1"
                    )
                )
                if config_grouping[config_class]['wechat_common'][arg]['type'] == "bool":
                    scrollable_content.controls.append(
                        ft.Switch(
                            label=arg,
                            value=conf().get(arg),
                            on_change=lambda e,key=arg:handle_value_change(e,key,"wechat_common")
                        )
                    )
                else:
                    scrollable_content.controls.append(
                        ft.TextField(
                            label=arg,
                            value=conf().get(arg),
                            color="#000000",
                            on_change=lambda e,key=arg:handle_value_change(e,key)
                        )
                    )

        dynamic_content.controls.append(scrollable_content)
        page.update()

        def handle_value_change(event, key, current_select='wechat_common'):
            raw_value = event.control.value
            print("raw_value:",raw_value)
            config_type = config_grouping[config_class][current_select][key]['type']
            try:
                if config_type == "str":
                    converted_value = str(raw_value)
                elif config_type == "int":
                    converted_value = int(raw_value)
                elif config_type == "bool":
                    converted_value = raw_value
                else:
                    raise ValueError(f"Unsupported type: {config_type}")
            except ValueError as e:
                # 如果转换失败，可以在这里处理错误（例如显示提示信息）
                print(f"Error converting value for key '{key}': {e}")
                return
            conf().set(key, converted_value)

    def update_config(e):
        save_config()

        page.snack_bar = ft.SnackBar( # ====这个为啥没显示
            content=ft.Text("配置已保存！", size=16, color="#FFFFFF"),
            bgcolor="#4CAF50",
            duration=2000
        )

        load_config()
        page.snack_bar.open = True
        page.update()

    def update_button_style(running=False): # 更新运行按钮样式
        for btn in [channel_run_button, model_run_button]:
            if running:
                btn.content = ft.Row(
                    [
                        ft.Icon(ft.icons.STOP_CIRCLE, color="#FFFFFF", size=22),
                        ft.Text("停止运行", size=22, color="#FFFFFF")
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=5
                )
                btn.bgcolor = "#2196F3"
                btn.on_click = kill_process
                btn.on_hover = lambda e: on_hover_pause(e)
            else:
                btn.content = ft.Row(
                    [
                        ft.Icon(ft.icons.PLAY_ARROW, color="#FFFFFF", size=22),
                        ft.Text("开始运行", size=22, color="#FFFFFF")
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=5
                )
                btn.bgcolor = "#4CAF50"
                btn.on_click = start_run_app
                btn.on_hover = None
            btn.update()

    def on_hover_pause(e): # 运行按钮悬停样式
        for btn in [channel_run_button, model_run_button]:
            if e.data == "true":  # 鼠标进入
                btn.bgcolor = "#FF5722"  # 红色
                btn.content = ft.Row(
                    [
                        ft.Icon(ft.icons.PAUSE_CIRCLE, color="#FFFFFF", size=22),
                        ft.Text("暂停运行", size=22, color="#FFFFFF")
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=5
                )
            else:  # 鼠标离开
                btn.bgcolor = "#2196F3"  # 蓝色
                btn.content = ft.Row(
                    [
                        ft.Icon(ft.icons.STOP_CIRCLE, color="#FFFFFF", size=22),
                        ft.Text("正在运行", size=22, color="#FFFFFF")
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=5
                )
            btn.update()

    # 运行管理
    def start_run_app(e):
        start_run()

    def start_run():
        global current_process_instance

        if current_process_instance and current_process_instance.is_alive():
            os.kill(current_process_instance.pid, signal.SIGTERM)  # 杀掉当前进程
            current_process_instance.join()  # 等待当前进程结束

        current_process_instance = Process(target=run)
        current_process_instance.start()
        update_button_style(running=True)

    def kill_process(e=None):
        """这里是按钮关闭运行转发的代码"""
        global current_process_instance
        if current_process_instance is not None:
            os.kill(current_process_instance.pid, signal.SIGTERM)  # 杀掉当前进程
            update_button_style(running=False)

    # 数据中心页部分
    class LogViewManager: # 日志页更新管理及样式设置
        def __init__(self):
            self.base_width = 400
            self.base_height = 450
            self.is_expanded = False
            self.log_base_height = 360
            self.log_expand_height = 620

        def create_log_view(self, page: ft.Page):
            self.page = page
            self.log_view = ft.ListView(
                expand=True,
                spacing=5,
                auto_scroll=True,
                controls=[ft.Text("日志初始化完成...", color="white")]
            )

            self.log_view_container = ft.Container(
                content=self.log_view,
                height=self.log_base_height,  # 初始高度为 360
                border=ft.border.all(1, "#000000"),
                padding=10,
                border_radius=5
            )

            self.log_container = ft.Container(
                content=ft.Column(
                    [
                        ft.Text("运行日志", size=30, weight=ft.FontWeight.BOLD,color="#FFFFFF"),
                        self.log_view_container,
                    ]
                ),
                width=self.base_width,
                height=self.base_height,
                bgcolor="#000000",
                border_radius=10,
                padding=20,
                on_click=self.toggle_size,
            )
            return self.log_container

        def start_log_watcher(self):
            """启动日志文件监控"""
            event_handler = LogFileHandler(self)
            event_handler.start()

        def toggle_size(self, e):
            if self.is_expanded:
                self.log_container.width = self.base_width
                self.log_container.height = self.base_height
                self.log_view.spacing = 5
                self.log_view_container.height = self.log_base_height
            else:
                self.log_container.width = 1050
                self.log_container.height = 710
                self.log_view.spacing = 10
                self.log_view_container.height = self.log_expand_height

            self.is_expanded = not self.is_expanded
            self.log_container.update()

    log_manager = LogViewManager()
    chart_container = grapg(page)

    reply_count = ft.Text("0", color="#000000", size=30)
    friends_count = ft.Text("0", color="#000000", size=30)
    ended_count = ft.Text("0", color="#000000", size=30)
    run_time = ft.Text("0", color="#000000", size=30)

    def realtime_data(): # 实时更新数据汇总页的数据
        nonlocal running
        while running:
            today_stats = get_today_stats()
            reply_count.value = str(today_stats["reply_count"])
            friends_count.value = str(today_stats["new_friends"])
            ended_count.value = str(today_stats["ended_conversations"])
            run_time.value = "53小时"
            # chart_container = grapg(page)
            page.update()
            time.sleep(3)

    # 渠道管理页部分
    channel_dynamic_content = ft.Column(expand=True)

    # 模型管理页部分
    model_dynamic_content = ft.Column(expand=True)

    # 使用文档部分
    shakeble_button = ft.ElevatedButton(
        text="了解更多私域知识",
        bgcolor="#000000",
        color="#FFFFFF",
        height=40,
        width=200,
        url="www.baidu.com"
    )
    shaking = asyncio.Event()

    async def shake_button():
        while shaking.is_set():
            shakeble_button.offset = ft.transform.Offset(
                random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1)
            )
            shakeble_button.update()
            await asyncio.sleep(0.05)  # 控制抖动速度

        shakeble_button.offset = ft.transform.Offset(0, 0)
        shakeble_button.update()

    def shakeble_button_on_hover(e):
        if e.data == "true":
            if not shaking.is_set():
                shaking.set()
                asyncio.run_coroutine_threadsafe(shake_button(), page.loop)
        else:
            shaking.clear()

    shakeble_button.on_hover = shakeble_button_on_hover

    # 页面构造部分
    navbar_button_style = ft.ButtonStyle( # 导航栏按钮
        color="#000000",
        bgcolor="#FFFFFF",
        padding=ft.padding.all(10),
        shape=ft.RoundedRectangleBorder(radius=5),
        overlay_color="#EDEBEB",
    )

    def create_run_button():
        return ft.ElevatedButton(
            content=ft.Row(
                [
                    ft.Icon(ft.icons.PLAY_ARROW, color="#FFFFFF", size=22),
                    ft.Text("开始运行",size=22,color="#FFFFFF")
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=5
            ),
            on_click=start_run_app,
            bgcolor="#4CAF50",
            color="#FFFFFF",
            width=150,
            height=60,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=5)
            )
        )

    channel_run_button = create_run_button()
    model_run_button = create_run_button()

    # ================================================
    # =================>>>静态页面部分<<<===============
    # ================================================

    navbar_container = ft.Container( # 左侧导航栏
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Image(
                        src="https://longshangai.oss-cn-beijing.aliyuncs.com/software_assets/logo.png",
                        width=250,
                        height=100
                    ),
                    margin=ft.margin.only(bottom=10),
                ),
                ft.Text("龙商学院-AI客服", color="#000000", size=26, weight=ft.FontWeight.BOLD),
                ft.Text("望龙", color="#666666", size=14),
                ft.Container(height=25),
                ft.TextButton("数据中心", on_click=show_infocenter,style=navbar_button_style,width=200,height=40),
                ft.TextButton("渠道管理", on_click=show_channel,style=navbar_button_style,width=200,height=40),
                ft.TextButton("模型管理", on_click=show_model,style=navbar_button_style,width=200,height=40),
                ft.TextButton("使用文档", on_click=show_doc,style=navbar_button_style,width=200,height=40),
                ft.Container(height=160),
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(
                            icon=ft.icons.POWER_SETTINGS_NEW,
                            icon_size=30,
                            on_click=close_app,
                            icon_color="#F80000"
                        ),
                        ft.IconButton(
                            icon=ft.icons.VISIBILITY_OFF,
                            icon_size=30,
                            on_click=minimze_to_tray,
                            icon_color="#808B93"
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    )
                )
            ],
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor="#FFFFFF",
        border_radius=20,
        width=300,
        height=760,
        padding=20
    )

    infocenter_container = ft.Container( # 数据中心页面
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Row(
                        [
                            log_manager.create_log_view(page),
                            chart_container
                        ]
                    )
                ),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text("数据汇总", color="#000000", size=30, weight=ft.FontWeight.BOLD),
                                        ft.Text("企业专业定制版", color="#000000", size=15),
                                    ]
                                ),
                                width = 250,
                                height = 250
                            ),
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text("回复次数", color="#000000", size=20, weight=ft.FontWeight.BOLD),
                                        reply_count
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                                ),
                                bgcolor="#FFFFFF",
                                border_radius=10,
                                width=150,
                                height=150,
                                margin=15,
                                padding=20
                            ),
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text("新增好友", color="#000000", size=20, weight=ft.FontWeight.BOLD),
                                        friends_count
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                                ),
                                bgcolor="#FFFFFF",
                                border_radius=10,
                                width=150,
                                height=150,
                                margin=15,
                                padding=20
                            ),
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text("激活次数", color="#000000", size=20, weight=ft.FontWeight.BOLD),
                                        ended_count
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                                ),
                                bgcolor="#FFFFFF",
                                border_radius=10,
                                width=150,
                                height=150,
                                margin=15,
                                padding=20
                            ),
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text("运行时长", color="#000000", size=20, weight=ft.FontWeight.BOLD),
                                        run_time
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                                ),
                                bgcolor="#FFFFFF",
                                border_radius=10,
                                width=150,
                                height=150,
                                margin=15,
                                padding=20
                            )
                        ]
                    ),
                    bgcolor="#D6BBA6",  # 比 #C0C0A4 更深的颜色
                    border_radius=10,  # 圆角半径
                    width=1150,  # 宽度略小于父容器
                    height=250,  # 高度为父容器的一半
                    padding=20,  # 内边距
                ),
            ]
        ),
        bgcolor="#EDEBEB",
        border_radius=20,
        width=1100,
        height=760,
        padding=25
    )

    channel_container = ft.Container( # 渠道管理页面
        content=ft.Column( # 整体是竖排的
            [
                ft.Container( # 这里面是竖排的内容
                    content=ft.Row(
                        [ # 这儿是上面的横排内容
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text("请选择需要运行的渠道：", color="#000000", size=20, weight=ft.FontWeight.BOLD),
                                        ft.Dropdown(
                                            options=[
                                                ft.dropdown.Option("gewechat"),
                                                ft.dropdown.Option("sikulix"),
                                                ft.dropdown.Option("wcf"),
                                                ft.dropdown.Option("wework"),
                                                ft.dropdown.Option("wecommix"),
                                                ft.dropdown.Option("wechatcom_service"),
                                                ft.dropdown.Option("wechatmp"),
                                                ft.dropdown.Option("wechatcom_app"),
                                            ],
                                            on_change=lambda e: update_parameters(
                                                dynamic_content=channel_dynamic_content,
                                                config_class="channel_type",
                                                e=e
                                            ),
                                            width=300,
                                            hint_text=conf().get("channel_type"),
                                            value=conf().get("channel_type"),
                                            color="#000000"
                                        )
                                    ],
                                    alignment=ft.MainAxisAlignment.START
                                ),
                                expand=True
                            ),
                            ft.ElevatedButton(  # 保存参数按钮
                                content=ft.Row(
                                    [
                                        ft.Icon(ft.icons.SAVE,color="#FFFFFF",size=22),
                                        ft.Text("保存参数",size=22,color="#FFFFFF")
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=5
                                ),
                                on_click=update_config,
                                bgcolor="#2196F3",
                                color="#FFFFFF",
                                width=150,
                                height=60,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=5)
                                )
                            ),
                            channel_run_button
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        spacing=20
                    )
                ),
                ft.Divider(height=20),
                channel_dynamic_content
            ],
            alignment=ft.MainAxisAlignment.START,
            expand=True
        ),
        bgcolor="#EDEBEB",
        border_radius=20,
        width=1100,
        height=760,
        padding=25
    )

    model_container = ft.Container( # 模型管理页面
        content=ft.Column( # 整体是竖排的
            [
                ft.Container( # 这里面是竖排的内容
                    content=ft.Row(
                        [ # 这儿是上面的横排内容
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text("请选择需要运行的模型：", color="#000000", size=20, weight=ft.FontWeight.BOLD),
                                        ft.Dropdown(
                                            options=[ft.dropdown.Option("dify"), ft.dropdown.Option("coze"), ft.dropdown.Option("openai")],
                                            on_change=lambda e: update_parameters(
                                                dynamic_content=model_dynamic_content,
                                                config_class="model",
                                                e=e
                                            ),
                                            width=300,
                                            hint_text=conf().get("model"),
                                            value=conf().get("model"),
                                            color="#000000"
                                        )
                                    ],
                                    alignment=ft.MainAxisAlignment.START
                                ),
                                expand=True
                            ),
                            ft.ElevatedButton(  # 保存参数按钮
                                content=ft.Row(
                                    [
                                        ft.Icon(ft.icons.SAVE,color="#FFFFFF",size=22),
                                        ft.Text("保存参数",size=22,color="#FFFFFF")
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=5
                                ),
                                on_click=update_config,
                                bgcolor="#2196F3",
                                color="#FFFFFF",
                                width=150,
                                height=60,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=5)
                                )
                            ),
                            model_run_button
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        spacing=20
                    )
                ),
                ft.Divider(height=20),
                model_dynamic_content
            ],
            alignment=ft.MainAxisAlignment.START,
            expand=True
        ),
        bgcolor="#EDEBEB",
        border_radius=20,
        width=1100,
        height=760,
        padding=25
    )

    doc_container = ft.Container( # 文档管理页面
        content=ft.ListView(
            [
                ft.Text("团队支持：", size=30, weight=ft.FontWeight.BOLD, color="#000000"),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Image(
                                src="https://longshangai.oss-cn-beijing.aliyuncs.com/software_assets/%E6%9C%9B%E9%BE%99%E4%BA%8C%E7%BB%B4%E7%A0%81.jpg",
                                height=400,
                                width=350,
                                fit=ft.ImageFit.FIT_WIDTH
                            ),
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text("望龙本龙联系方式", size=20, weight=ft.FontWeight.BOLD, color="#000000"),
                                        ft.Text(
                                            value="望龙是来自西安的顶级私域操盘手，在前端流量获客方面有着无可匹敌的优势与经验",
                                            size=12,
                                            color="#4D4D4D"
                                        ),
                                        shakeble_button
                                    ],
                                ),
                                expand=True,
                                alignment=ft.alignment.top_left,
                                margin=ft.margin.only(left=10)
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                ),
                ft.Text("使用文档：", size=30, weight=ft.FontWeight.BOLD, color="#000000"),
                ft.Text("🧐数据中心页面介绍", size=20, weight=ft.FontWeight.BOLD, color="#000000"),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.ElevatedButton(
                                text="页面介绍",
                                url="https://qcnmanduqh7k.feishu.cn/wiki/TgXTwrasri3XqlkbhRQcttGunOb?from=from_copylink",
                                height=40,
                                width=100
                            )
                        ]
                    ),
                    margin=ft.margin.only(left=30)
                ),
                ft.Text("🥳渠道管理", size=20, weight=ft.FontWeight.BOLD, color="#000000"),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("个人微信：", size=15, weight=ft.FontWeight.BOLD, color="#000000"),
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.ElevatedButton(
                                            text="gewechat",
                                            url="https://qcnmanduqh7k.feishu.cn/wiki/S6kawPZoFieuwckdOJvcaQLonGf?from=from_copylink",
                                            height=40,
                                            width=100
                                        ),
                                        ft.ElevatedButton(
                                            text="wcf",
                                            url="www.baidu.com",
                                            height=40,
                                            width=100
                                        )
                                    ]
                                )
                            ),
                            ft.Text("企业微信：", size=15, weight=ft.FontWeight.BOLD, color="#000000"),
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.ElevatedButton(
                                            text="sikulix",
                                            url="www.baidu.com",
                                            height=40,
                                            width=100
                                        ),
                                        ft.ElevatedButton(
                                            text="wecommix",
                                            url="https://qcnmanduqh7k.feishu.cn/wiki/Nl8FwYoTsi2qAtkDW9ycOVqnn7b?from=from_copylink",
                                            height=40,
                                            width=100
                                        ),
                                        ft.ElevatedButton(
                                            text="wework",
                                            url="www.baidu.com",
                                            height=40,
                                            width=100
                                        )
                                    ]
                                )
                            ),
                        ]
                    ),
                    margin=ft.margin.only(left=30)
                ),
                ft.Text("🤗模型管理", size=20, weight=ft.FontWeight.BOLD, color="#000000"),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.ElevatedButton(
                                text="dify",
                                url="www.baidu.com",
                                height=40,
                                width=100
                            ),
                            ft.ElevatedButton(
                                text="coze",
                                url="www.baidu.com",
                                height=40,
                                width=100
                            )
                        ]
                    ),
                    margin=ft.margin.only(left=30)
                ),
            ],
            spacing=10,
        ),
        bgcolor="#EDEBEB",
        border_radius=20,
        width=1100,
        height=760,
        padding=25
    )

    # 主页面
    rounded_container = ft.WindowDragArea(
        ft.Container(
            content=ft.Row(
                [
                    navbar_container,
                    infocenter_container,
                    channel_container,
                    model_container,
                    doc_container
                ],
                expand=True,
            ),
            bgcolor="#FFFFFF",
            border_radius=20,
            padding=0,
            expand=True,
            width=1400,
            height=760,
        ),
        maximizable=False
    )

    page.add(rounded_container)

    log_manager.start_log_watcher()
    realtime_data()



def main_entry():
    try:
        if not VerifyAccess().check_local_license():
            win = Win()
            win.mainloop()
        else:
            ft.app(target=main)
    except Exception as e:
        print(e)

# ==================================================
# ==========>>>---    下面的不用看了   ---<<<==========
# ==================================================

class LogFileHandler:
    def __init__(self, log_view_manager):
        self.log_view_manager = log_view_manager
        self.last_position = 0  # 记录上次读取的位置


    def start(self):
        add_log_listener(lambda log: self.update(log))

    def update(self, log: str):
        self.log_view_manager.log_view.controls.append(
                    ft.Text(log.strip(), color="white", selectable=True)
                )
        self.log_view_manager.log_view.update()


class WinGUI(Tk):
    def __init__(self):
        super().__init__()
        self.__win()
        self.tk_label_m7nw1oae = self.__tk_label_m7nw1oae(self)
        self.tk_text_m7nw2g9w = self.__tk_text_m7nw2g9w(self)
        self.tk_label_m7nw2rgf = self.__tk_label_m7nw2rgf(self)
        self.tk_input_m7nw3u68 = self.__tk_input_m7nw3u68(self)
        self.tk_button_m7nw4dr9 = self.__tk_button_m7nw4dr9(self)

    def __win(self):
        self.title("激活界面")
        # 设置窗口大小、居中
        width = 600
        height = 317
        screenwidth = self.winfo_screenwidth()
        screenheight = self.winfo_screenheight()
        geometry = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
        self.geometry(geometry)

        self.resizable(width=False, height=False)

    def scrollbar_autohide(self, vbar, hbar, widget):
        """自动隐藏滚动条"""

        def show():
            if vbar: vbar.lift(widget)
            if hbar: hbar.lift(widget)

        def hide():
            if vbar: vbar.lower(widget)
            if hbar: hbar.lower(widget)

        hide()
        widget.bind("<Enter>", lambda e: show())
        if vbar: vbar.bind("<Enter>", lambda e: show())
        if vbar: vbar.bind("<Leave>", lambda e: hide())
        if hbar: hbar.bind("<Enter>", lambda e: show())
        if hbar: hbar.bind("<Leave>", lambda e: hide())
        widget.bind("<Leave>", lambda e: hide())

    def v_scrollbar(self, vbar, widget, x, y, w, h, pw, ph):
        widget.configure(yscrollcommand=vbar.set)
        vbar.config(command=widget.yview)
        vbar.place(relx=(w + x) / pw, rely=y / ph, relheight=h / ph, anchor='ne')

    def h_scrollbar(self, hbar, widget, x, y, w, h, pw, ph):
        widget.configure(xscrollcommand=hbar.set)
        hbar.config(command=widget.xview)
        hbar.place(relx=x / pw, rely=(y + h) / ph, relwidth=w / pw, anchor='sw')

    def create_bar(self, master, widget, is_vbar, is_hbar, x, y, w, h, pw, ph):
        vbar, hbar = None, None
        if is_vbar:
            vbar = Scrollbar(master)
            self.v_scrollbar(vbar, widget, x, y, w, h, pw, ph)
        if is_hbar:
            hbar = Scrollbar(master, orient="horizontal")
            self.h_scrollbar(hbar, widget, x, y, w, h, pw, ph)
        self.scrollbar_autohide(vbar, hbar, widget)

    def __tk_label_m7nw1oae(self, parent):
        label = Label(parent, text="您的账户为：", anchor="center", )
        label.place(x=20, y=10, width=76, height=30)
        return label

    def __tk_text_m7nw2g9w(self, parent):
        text = Text(parent)
        text.place(x=105, y=10, width=483, height=100)
        return text

    def __tk_label_m7nw2rgf(self, parent):
        label = Label(parent, text="请输入密钥：", anchor="center", )
        label.place(x=20, y=130, width=79, height=30)
        return label

    def __tk_input_m7nw3u68(self, parent):
        ipt = Entry(parent, )
        ipt.place(x=105, y=130, width=483, height=100)
        return ipt

    def __tk_button_m7nw4dr9(self, parent):
        btn = Button(parent, text="按钮", takefocus=False, )
        btn.place(x=19, y=250, width=569, height=50)
        return btn


class Win(WinGUI):
    def __init__(self):
        super().__init__()
        self.__event_bind()
        self.verify = VerifyAccess()
        self.i = 0
        self.tk_text_m7nw2g9w.insert("1.0", self.verify.token)

    def __event_bind(self):
        self.tk_button_m7nw4dr9.configure(command=self.on_verify)

    def __style_config(self):
        pass

    def on_verify(self):
        try:
            code = self.tk_input_m7nw3u68.get()
            print(f"尝试验证代码：{code}")  # 调试输出
            if self.verify.verify(code):
                print("激活成功")
                self.destroy()
                ft.app(target=main)
            else:
                self.i += 1
                print(f"激活失败，剩余尝试次数: {3 - self.i}")
                if self.i >= 3:
                    print("尝试次数超限")
                    self.destroy()
                    exit()
        except Exception as e:
            print(f"发生异常：{str(e)}")  # 异常捕获


if __name__ == '__main__':
    from multiprocessing import freeze_support

    freeze_support()

    # 只有主进程会执行 GUI 入口
    main_entry()


