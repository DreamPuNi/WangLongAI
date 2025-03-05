import flet as ft


def main(page: ft.Page):
    page.title = "基本填充按钮"
    page.add(
        ft.FilledButton(text="填充按钮"),
        ft.FilledButton("禁用按钮", disabled=True),
        ft.FilledButton("带图标的按钮", icon="add"),
    )

ft.app(target=main)