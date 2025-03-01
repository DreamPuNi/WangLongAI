@echo off
REM 切换到项目目录
cd /d %~dp0

REM 激活虚拟环境
call venv\Scripts\activate

REM 启动 Python 脚本
python fuck_webui.py

REM 检查脚本是否成功运行
if %errorlevel% neq 0 (
    echo 脚本运行出错，请检查错误信息！
)

REM 防止窗口自动关闭
pause