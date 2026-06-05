"""
vnpy_autorepay - Auto Repay App for vnpy
融资账户自动还款应用

功能特性：
- 支持融资账户的自动化现金还款操作
- 支持定时执行和间隔执行两种触发方式
- 提供直观的图形用户界面进行账户管理和任务配置
- 实现账户信息加密存储
- 记录所有还款操作的详细日志
- 具备完善的错误处理机制

使用方式：
1. 在VeighNa Trader中启动自动还款应用
2. 在账户管理页面添加融资账户信息
3. 在还款设置页面创建还款任务
4. 在任务监控页面查看执行状态和历史记录
"""

from pathlib import Path

from vnpy.trader.app import BaseApp

from .engine import AutorepayEngine, APP_NAME


__version__ = "1.0.0"


class AutorepayApp(BaseApp):
    """自动还款应用"""

    app_name: str = APP_NAME
    app_module: str = __module__
    app_path: Path = Path(__file__).parent
    display_name: str = "自动还款"
    engine_class: type[AutorepayEngine] = AutorepayEngine
    widget_name: str = "AutorepayManager"
    icon_name: str = str(app_path.joinpath("autorepay.ico"))
