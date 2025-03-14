import flet as ft
import random
import asyncio


def main(page: ft.Page):
    page.title = "疯狂抖动按钮"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER





    button = ft.ElevatedButton(text="别碰我！")

    # 控制抖动的状态
    shaking = asyncio.Event()

    async def shake_button():
        """让按钮无限抖动，直到 shaking 被清除"""
        while shaking.is_set():
            button.offset = ft.transform.Offset(
                random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1)
            )
            button.update()
            await asyncio.sleep(0.05)  # 控制抖动速度

        # 鼠标移开后，按钮回到原位
        button.offset = ft.transform.Offset(0, 0)
        button.update()

    def on_hover(e):
        """鼠标悬停时触发抖动，鼠标移开时停止"""
        if e.data == "true":
            if not shaking.is_set():  # 避免重复创建任务
                shaking.set()
                asyncio.run_coroutine_threadsafe(shake_button(), page.loop)
        else:
            shaking.clear()  # 停止抖动

    button.on_hover = on_hover
    page.add(button)


ft.app(target=main)
