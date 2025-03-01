import os
import sys
import time
import json
import signal
import threading
import flet as ft
from PIL import Image

from common.log import log_queue
from plugins import *
from common import const
from channel import channel_factory
from multiprocessing import Process
from pystray import Icon, Menu, MenuItem
from fuck_webui import check_gewechat_online
from config import conf, load_config, save_config

from common.verify import VerifyAccess
from tkinter import *
from tkinter.ttk import *

# 线程管理
current_process_instance = None

def run():
    try:
        # load config
        load_config()
        # create channel
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


# 主页面
def main(page: ft.Page):
    load_config()
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


    # 路由管理部分
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


    # 动态组件部分
    def minimze_to_tray(e):
        page.window.minimized = True
        page.update()

    def close_app(e):
        kill_process()
        page.window.destroy()

    def update_parameters(dynamic_content, config_class, e):
        current_select = e.control.value
        with open("config_grouping.json", "r", encoding="utf-8") as f:
            config_grouping = json.load(f)
        dynamic_content.controls.clear()
        scrollable_content = ft.ListView(expand=True, spacing=10, height=600)

        conf().set(config_class,current_select)

        if config_class == "channel_type":
            if current_select == "gewechat":
                scrollable_content.controls.append(
                    ft.Text(value="Gewe登录信息", size=22, weight=ft.FontWeight.BOLD, color="#000000")
                )
                if check_gewechat_online()[0]:
                    scrollable_content.controls.append(
                        ft.Column([
                            ft.Container(
                                content=ft.Image(src="tmp/avatar.png",width=150,height=150),
                                margin=ft.margin.only(right=40)
                            ),

                        ])
                    )
                # 首先检查是否在线，如果在线就显示头像和其他信息，并且添加一个退出登陆的按钮
                # 如果不在线就显示二维码
                pass
            scrollable_content.controls.append(
                ft.Text(value="微信公共参数设置", size=22, weight=ft.FontWeight.BOLD, color="#000000")
            )
            for arg in config_grouping[config_class]["wechat_common"]:
                scrollable_content.controls.append(
                    ft.Text(
                        value=f"{config_grouping[config_class]["wechat_common"][arg]["tittle"]}",
                        size=16,
                        color="#000000",
                        weight=ft.FontWeight.BOLD)
                )
                scrollable_content.controls.append(
                    ft.Text(
                        value=f"{config_grouping[config_class]["wechat_common"][arg]["describe"]}",
                        size=12,
                        color="#9B9FA1"
                    )
                )
                scrollable_content.controls.append(
                    ft.TextField(
                        label=arg,
                        value=conf().get(arg),
                        color="#000000",
                        on_change=lambda e,key=arg:conf().set(key,e.control.value)
                    )
                )
            scrollable_content.controls.append(ft.Divider(height=15, color="#CCCCCC"))

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
                    value=f"{config_grouping[config_class][current_select][arg]["tittle"]}",
                    size=16,
                    color="#000000",
                    weight=ft.FontWeight.BOLD
                )
            )
            scrollable_content.controls.append(
                ft.Text(
                    value=f"{config_grouping[config_class][current_select][arg]["describe"]}",
                    size=12,
                    color="#9B9FA1"
                )
            )
            scrollable_content.controls.append(
                ft.TextField(
                    label=arg,
                    value=conf().get(arg),
                    color="#000000",
                    on_change=lambda e,key=arg:conf().set(key, e.control.value)
                )
            )
        dynamic_content.controls.append(scrollable_content)
        page.update()

    def update_config(e):
        save_config()
        page.snack_bar = ft.SnackBar(
            content=ft.Text("配置已保存！", size=16, color="#FFFFFF"),
            bgcolor="#4CAF50",
            duration=2000
        )
        page.snack_bar.open = True
        page.update()

    def start_run_app(e):
        start_run()


    def start_run():
        global current_process_instance

        if current_process_instance and current_process_instance.is_alive():
            os.kill(current_process_instance.pid, signal.SIGTERM)  # 杀掉当前进程
            current_process_instance.join()  # 等待当前进程结束

        current_process_instance = Process(target=run)
        current_process_instance.start()

    def kill_process():
        global current_process_instance
        if current_process_instance is not None and current_process_instance.is_alive():
            os.kill(current_process_instance.pid, signal.SIGTERM)  # 杀掉当前进程

    # 数据中心
    class LogViewManager:
        def __init__(self):
            self.base_width = 400
            self.base_height = 450
            self.is_expanded = False

        def create_log_view(self):
            self.log_view = ft.ListView(
                expand=True,
                spacing=10,
                auto_scroll=True,
                controls=[ft.Text("日志初始化完成...", color="white")],
            )

            self.log_container = ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("运行日志", size=30, weight=ft.FontWeight.BOLD),
                                ft.IconButton(
                                    icon=ft.icons.ZOOM_OUT_MAP,
                                    on_click=self.toggle_size,
                                    tooltip="切换窗口大小",
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Container(
                            content=self.log_view,
                            height=350,  # 留出标题栏空间
                            border=ft.border.all(1, "#FFFFFF"),
                            padding=10
                        )
                    ]
                ),
                width=self.base_width,
                height=self.base_height,
                bgcolor="#808B93",
                border_radius=10,
                padding=20
            )
            return self.log_container

        def toggle_size(self, e):
            if self.is_expanded:
                self.log_container.width = self.base_width
                self.log_container.height = self.base_height
            else:
                self.log_container.width = 800
                self.log_container.height = 600
            self.is_expanded = not self.is_expanded
            self.log_container.update()
    log_manager = LogViewManager()

    def update_logs(e=None):
        try:
            while not log_queue.empty():
                log_entry = log_queue.get_nowait()
                if len(log_manager.log_view.controls) > 100:  # 保持最近100条日志
                    log_manager.log_view.controls.pop(0)
                log_manager.log_view.controls.append(
                    ft.Text(log_entry, color="white", selectable=True)
                )
                log_manager.log_view.update()
        except Exception as e:
            logger.error(f"Log update error: {str(e)}")
        ft.Timer(0.1,update_logs,repeat=True).start()

    # 渠道管理页部分
    channel_dynamic_content = ft.Column(expand=True)

    # 模型管理页部分
    model_dynamic_content = ft.Column(expand=True)

    # 页面构造部分
    navbar_button_style = ft.ButtonStyle(
        color="#000000",
        bgcolor="#FFFFFF",
        padding=ft.padding.all(10),
        shape=ft.RoundedRectangleBorder(radius=5),
        overlay_color="#EDEBEB",
    )

    power_dialog = ft.Dropdown(
        options=[
            ft.dropdown.Option("最小化到系统托盘",),
            ft.dropdown.Option("关闭应用",)
        ],
        visible=True,
    )

    navbar_container = ft.Container( # 左侧导航栏
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Image(src="logo.png",width=250,height=100),
                    margin=ft.margin.only(bottom=10),
                ),
                ft.Text("龙商学院-AI客服", color="#000000", size=26, weight=ft.FontWeight.BOLD),
                ft.Text("望龙", color="#666666", size=14),
                ft.Container(height=25),
                ft.TextButton("数据中心", on_click=show_infocenter,style=navbar_button_style,width=200,height=40),
                ft.TextButton("渠道管理", on_click=show_channel,style=navbar_button_style,width=200,height=40),
                ft.TextButton("模型管理", on_click=show_model,style=navbar_button_style,width=200,height=40),
                ft.TextButton("使用文档", on_click=show_doc,style=navbar_button_style,width=200,height=40),
                ft.Container(height=20),
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
                            log_manager.create_log_view(),
                            ft.Container(
                                content=ft.Text("流量监控", color="#000000", size=30, weight=ft.FontWeight.BOLD),
                                bgcolor="#94CED8",
                                border_radius=10,
                                width=640,
                                height=450,
                                padding=20
                            )
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
                                content=ft.Text("回复次数", color="#000000", size=20),
                                bgcolor="#FFFFFF",
                                border_radius=10,
                                width=150,
                                height=150,
                                margin=15,
                                padding=20
                            ),
                            ft.Container(
                                content=ft.Text("新增好友", color="#000000", size=20),
                                bgcolor="#FFFFFF",
                                border_radius=10,
                                width=150,
                                height=150,
                                margin=15,
                                padding=20
                            ),
                            ft.Container(
                                content=ft.Text("留资数量", color="#000000", size=20),
                                bgcolor="#FFFFFF",
                                border_radius=10,
                                width=150,
                                height=150,
                                margin=15,
                                padding=20
                            ),
                            ft.Container(
                                content=ft.Text("运行时长", color="#000000", size=20),
                                bgcolor="#FFFFFF",
                                border_radius=10,
                                width=150,
                                height=150,
                                margin=15,
                                padding=20
                            ),
                            ft.Container(
                                content=ft.Text("更多教程", color="#000000", size=20),
                                bgcolor="#94CED8",
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
                                            options=[ft.dropdown.Option("gewechat"), ft.dropdown.Option("sikulix_wecom"), ft.dropdown.Option("wcf")],
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
                            ft.ElevatedButton(  # 运行/停止按钮
                                content=ft.Row(
                                    [
                                        ft.Icon(ft.icons.PLAY_ARROW, color="#FFFFFF",size=22),
                                        ft.Text("开始运行", size=22, color="#FFFFFF")
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
                            ft.ElevatedButton(  # 运行/停止按钮
                                content=ft.Row(
                                    [
                                        ft.Icon(ft.icons.PLAY_ARROW, color="#FFFFFF",size=22),
                                        ft.Text("开始运行", size=22, color="#FFFFFF")
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
        content=ft.Column(
            [
                ft.Text("请选择需要运行的渠道：", size=20, weight=ft.FontWeight.BOLD),
            ]
        ),
        bgcolor="#EDEBEB",
        border_radius=20,
        width=1100,
        height=760,
        padding=25
    )

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


def main_entry():
    if not VerifyAccess().check_local_license():
        win = Win()
        win.mainloop()
    else:
        ft.app(target=main)


# ==================================================
# ==========>>>---    下面的不用看了   ---<<<==========
# ==================================================

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


