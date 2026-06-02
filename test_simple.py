# flake8: noqa
"""
简化版测试脚本 - 仅测试 vnpy_autorepay
"""

import sys
sys.path.insert(0, "d:\\work\\vnpy_related_repo\\vnpy")
sys.path.insert(0, "d:\\work\\vnpy_related_repo\\vnpy\\vnpy_autorepay")

from vnpy_autorepay import AutorepayApp

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp


if __name__ == "__main__":
    """启动 vnpy_autorepay 应用"""
    qapp = create_qapp()

    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)

    # 只添加 autorepay 应用
    main_engine.add_app(AutorepayApp)

    main_window = MainWindow(main_engine, event_engine)
    main_window.showMaximized()

    qapp.exec()
