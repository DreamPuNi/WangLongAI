import flet as ft
from datetime import datetime, timedelta
from core.data.watch_dog import get_last_seven_days_prompt_usage

prompt_usage_list = get_last_seven_days_prompt_usage()

today = datetime.now()
dates = [(today - timedelta(days=i)).strftime("%m-%d") for i in range(1, 8)]

def grapg(page: ft.Page):
    data = [
        ft.LineChartData(
            data_points=[
                ft.LineChartDataPoint(0, prompt_usage_list[0]),
                ft.LineChartDataPoint(1, prompt_usage_list[1]),
                ft.LineChartDataPoint(2, prompt_usage_list[2]),
                ft.LineChartDataPoint(3, prompt_usage_list[3]),
                ft.LineChartDataPoint(4, prompt_usage_list[4]),
                ft.LineChartDataPoint(5, prompt_usage_list[5]),
                ft.LineChartDataPoint(6, prompt_usage_list[6]),
            ],
            color="#FFFFFF",
            stroke_width=3,
            curved=True,
            stroke_cap_round=True,
        ),
    ]

    chart = ft.LineChart(
        data_series=data,
        border=ft.Border(
            bottom=ft.BorderSide(4, ft.Colors.with_opacity(0.5, ft.Colors.ON_SURFACE))
        ),
        left_axis=ft.ChartAxis(
            labels=[
                ft.ChartAxisLabel(
                    value=0,
                    label=ft.Text("0K", size=14, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                ),
                ft.ChartAxisLabel(
                    value=5000,
                    label=ft.Text("5K", size=14, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                ),
                ft.ChartAxisLabel(
                    value=10000,
                    label=ft.Text("1W", size=14, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                ),
                ft.ChartAxisLabel(
                    value=50000,
                    label=ft.Text("5W", size=14, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                ),
                ft.ChartAxisLabel(
                    value=100000,
                    label=ft.Text("10W", size=14, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                ),
            ],
            labels_size=40,
        ),
        bottom_axis=ft.ChartAxis(
            labels=[
                ft.ChartAxisLabel(
                    value=0,
                    label=ft.Container(
                        ft.Text(
                            dates[6],
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color="#FFFFFF",
                        ),
                        margin=ft.margin.only(top=10),
                    ),
                ),
                ft.ChartAxisLabel(
                    value=1,
                    label=ft.Container(
                        ft.Text(
                            dates[5],
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color="#FFFFFF",
                        ),
                        margin=ft.margin.only(top=10),
                    ),
                ),
                ft.ChartAxisLabel(
                    value=2,
                    label=ft.Container(
                        ft.Text(
                            dates[4],
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color="#FFFFFF",
                        ),
                        margin=ft.margin.only(top=10),
                    ),
                ),
                ft.ChartAxisLabel(
                    value=3,
                    label=ft.Container(
                        ft.Text(
                            dates[3],
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color="#FFFFFF",
                        ),
                        margin=ft.margin.only(top=10),
                    ),
                ),
                ft.ChartAxisLabel(
                    value=4,
                    label=ft.Container(
                        ft.Text(
                            dates[2],
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color="#FFFFFF",
                        ),
                        margin=ft.margin.only(top=10),
                    ),
                ),
                ft.ChartAxisLabel(
                    value=5,
                    label=ft.Container(
                        ft.Text(
                            dates[1],
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color="#FFFFFF",
                        ),
                        margin=ft.margin.only(top=10),
                    ),
                ),
                ft.ChartAxisLabel(
                    value=6,
                    label=ft.Container(
                        ft.Text(
                            dates[0],
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color="#FFFFFF",
                        ),
                        margin=ft.margin.only(top=10),
                    ),
                ),
            ],
            labels_size=32,
        ),
        right_axis=ft.ChartAxis(
            labels=[ft.ChartAxisLabel(
                    value=0,
                    label=ft.Container(),
                ),],
            labels_size=20
        ),
        bgcolor="#94CED8",
        min_y=0,
        max_y=max(prompt_usage_list)+500, # 这里需要根据参数的值进行灵活修改
        min_x=0,
        max_x=6,
        expand=True,
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("流量监控", color="#FFFFFF", size=30, weight=ft.FontWeight.BOLD),
                chart,  # 将图表嵌入到容器中
            ]
        ),
        bgcolor="#94CED8",
        border_radius=10,
        width=640,
        height=450,
        padding=20,
    )
