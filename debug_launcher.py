# flake8: noqa
"""
调试引导脚本 - 使用 debugpy 启动调试服务器
运行此脚本后，在 VS Code 中附加到远程调试
"""

import sys
import os

# 添加必要的路径
sys.path.insert(0, "d:\\work\\vnpy_related_repo\\vnpy")
sys.path.insert(0, "d:\\work\\vnpy_related_repo\\vnpy\\vnpy_autorepay")

# 导入 debugpy
import debugpy

# 配置调试服务器
DEBUG_PORT = 5678
DEBUG_HOST = "localhost"

print(f"启动调试服务器: {DEBUG_HOST}:{DEBUG_PORT}")
print("请在 VS Code 中配置远程调试并附加到该端口")

# 启动调试服务器（等待调试器连接）
debugpy.listen((DEBUG_HOST, DEBUG_PORT))
debugpy.wait_for_client()

print("调试器已连接，开始执行程序...")

# 现在导入并运行应用
from vnpy_autorepay import AutorepayApp
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp


if __name__ == "__main__":
    qapp = create_qapp()
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    
    # 添加 autorepay 应用
    main_engine.add_app(AutorepayApp)
    
    main_window = MainWindow(main_engine, event_engine)
    main_window.showMaximized()
    
    qapp.exec()
