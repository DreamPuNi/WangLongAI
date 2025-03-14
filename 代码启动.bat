@echo off
:: 设置当前目录为脚本所在目录
cd /d %~dp0

:: 检查是否存在虚拟环境文件夹
if not exist "venv" (
    echo 虚拟环境文件夹 'venv' 不存在，请先创建虚拟环境。
    pause
    exit /b 1
)

:: 激活虚拟环境
echo 正在激活虚拟环境...
call venv\Scripts\activate

:: 检查是否成功激活虚拟环境
if "%VIRTUAL_ENV%"=="" (
    echo 无法激活虚拟环境，请检查虚拟环境配置。
    pause
    exit /b 1
)

:: 检查是否存在 interface.py 文件
if not exist "interface.py" (
    echo 当前目录下未找到 interface.py 文件。
    pause
    exit /b 1
)

:: 运行 interface.py
echo 正在运行 interface.py...
python interface.py

:: 检查运行结果
if %ERRORLEVEL% neq 0 (
    echo 运行 interface.py 时发生错误。
    pause
    exit /b 1
)

:: 停止并退出
echo 程序运行完成。
pause
exit /b 0