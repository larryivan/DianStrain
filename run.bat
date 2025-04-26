@echo off
python gui.py
if %errorlevel% equ 0 (
    msg * "GUI.py 已经开启"
) else (
    msg * "GUI.py 启动失败，请检查Python环境"
)