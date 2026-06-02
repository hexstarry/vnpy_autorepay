"""
Base module for vnpy_autorepay
定义事件类型和常量
"""

from enum import Enum


APP_NAME: str = "autorepay"

EVENT_AUTOREPAY_LOG: str = "eAutorepayLog"
EVENT_AUTOREPAY_UPDATE: str = "eAutorepayUpdate"


class RepayStatus(Enum):
    """还款任务状态"""
    PENDING = "待执行"
    RUNNING = "执行中"
    SUCCESS = "成功"
    FAILED = "失败"
    CANCELLED = "已取消"


class RepayType(Enum):
    """还款触发类型"""
    FIXED_TIME = "定时执行"
    INTERVAL = "间隔执行"


class IntervalUnit(Enum):
    """时间间隔单位"""
    MINUTES = "分钟"
    HOURS = "小时"
    DAYS = "天"
    WEEKS = "周"
