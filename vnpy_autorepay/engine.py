"""
Autorepay Engine - Core functionality for automatic loan repayment
融资账户自动还款核心引擎
"""

import json
import time
import hashlib
from datetime import datetime, time as dt_time, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
from threading import Thread, Lock

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine
from vnpy.trader.object import AccountData, LogData
from vnpy.trader.event import EVENT_ACCOUNT, EVENT_TIMER
from vnpy.trader.utility import load_json, save_json, get_file_path

from .base import (
    APP_NAME,
    EVENT_AUTOREPAY_LOG,
    EVENT_AUTOREPAY_UPDATE,
    RepayStatus,
    RepayType,
    IntervalUnit
)

# 尝试导入 xtdata（迅投行情数据接口）
try:
    from xtquant import xtdata
    XT_QMT_AVAILABLE = True
except ImportError:
    XT_QMT_AVAILABLE = False


class RepayAccount:
    """融资账户信息"""
    
    def __init__(self):
        self.account_id: str = ""
        self.gateway_name: str = ""
        self.account_name: str = ""
        self.enabled: bool = True
        self.max_repay_amount: float = 0.0
        self.min_balance: float = 1000.0


class RepayTask:
    """还款任务配置"""
    
    def __init__(self):
        self.task_id: str = ""
        self.account_id: str = ""
        self.task_name: str = ""
        self.repay_type: RepayType = RepayType.FIXED_TIME
        
        # 定时执行设置
        self.fixed_time: dt_time = dt_time(15, 30)  # 默认下午3:30
        
        # 间隔执行设置
        self.interval_value: int = 24
        self.interval_unit: IntervalUnit = IntervalUnit.HOURS
        
        # 任务状态
        self.enabled: bool = True
        self.last_run_time: Optional[datetime] = None
        self.next_run_time: Optional[datetime] = None
        self.status: RepayStatus = RepayStatus.PENDING


class RepayRecord:
    """还款执行记录"""
    
    def __init__(self):
        self.record_id: str = ""
        self.task_id: str = ""
        self.task_name: str = ""
        self.account_id: str = ""
        self.account_name: str = ""
        self.gateway_name: str = ""
        self.execute_time: datetime = datetime.now()
        self.repay_amount: float = 0.0
        self.balance_before: float = 0.0
        self.balance_after: float = 0.0
        self.margin_loan_before: float = 0.0
        self.margin_loan_after: float = 0.0
        self.status: RepayStatus = RepayStatus.PENDING
        self.error_message: str = ""


class AutorepayEngine(BaseEngine):
    """自动还款引擎"""
    
    setting_filename: str = "autorepay_setting.json"
    account_filename: str = "autorepay_accounts.json"
    task_filename: str = "autorepay_tasks.json"
    record_filename: str = "autorepay_records.json"
    
    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        super().__init__(main_engine, event_engine, APP_NAME)
        
        self.accounts: Dict[str, RepayAccount] = {}
        self.tasks: Dict[str, RepayTask] = {}
        self.records: List[RepayRecord] = []
        
        self.lock: Lock = Lock()
        
        # 交易日历缓存
        self.trading_calendar_cache: Dict[str, set] = {}  # 格式: {"2024": {"20240101", "20240102", ...}}
        
        self.load_settings()
        self.register_event()
        
        # 初始化交易日历
        self._init_trading_calendar()
    
    def _init_trading_calendar(self) -> None:
        """初始化交易日历缓存"""
        if not XT_QMT_AVAILABLE:
            self.write_log("警告: xtdata模块不可用，将使用简单的周末判断")
            return
        
        try:
            # 获取当前年份和前后一年的交易日
            current_year = datetime.now().year
            years = [current_year - 1, current_year, current_year + 1]
            
            for year in years:
                start_time = f"{year}0101"
                end_time = f"{year}1231"
                
                try:
                    # 下载并获取交易日历
                    xtdata.download_holiday_data()
                    trading_days = xtdata.get_trading_calendar('SH', start_time, end_time)
                    
                    # 转换为集合存储，提高查询效率
                    trading_set = set(trading_days)
                    self.trading_calendar_cache[str(year)] = trading_set
                    
                    self.write_log(f"加载{year}年交易日历: {len(trading_set)}个交易日")
                except Exception as e:
                    self.write_log(f"加载{year}年交易日历失败: {str(e)}")
                    continue
                    
        except Exception as e:
            self.write_log(f"初始化交易日历失败: {str(e)}")
    
    def init_engine(self) -> None:
        """初始化引擎"""
        self.write_log("自动还款引擎启动")
    
    def register_event(self) -> None:
        """注册事件监听"""
        self.event_engine.register(EVENT_ACCOUNT, self.process_account_event)
        self.event_engine.register(EVENT_TIMER, self.process_timer_event)
    
    def process_account_event(self, event: Event) -> None:
        """处理账户事件"""
        account: AccountData = event.data
        pass
    
    def process_timer_event(self, event: Event) -> None:
        """处理定时事件"""
        now = datetime.now()
        
        for task_id, task in list(self.tasks.items()):
            if not task.enabled:
                continue
            
            if task.account_id not in self.accounts:
                continue
            
            if task.status == RepayStatus.RUNNING:
                continue
            
            if task.next_run_time and now >= task.next_run_time:
                self.execute_repay(task)
    
    def load_settings(self) -> None:
        """加载所有设置"""
        self.load_accounts()
        self.load_tasks()
        self.load_records()
    
    def load_accounts(self) -> None:
        """加载账户信息"""
        try:
            data: Dict = load_json(self.account_filename)
        except Exception:
            data = {}
        
        for account_id, account_data in data.items():
            try:
                account = RepayAccount()
                account.account_id = account_id
                account.gateway_name = account_data.get("gateway_name", "")
                account.account_name = account_data.get("account_name", "")
                account.enabled = account_data.get("enabled", True)
                account.max_repay_amount = account_data.get("max_repay_amount", 0.0)
                account.min_balance = account_data.get("min_balance", 1000.0)
                self.accounts[account_id] = account
            except Exception as e:
                self.write_log(f"解析账户失败: {str(e)}")
                continue
    
    def save_accounts(self) -> None:
        """保存账户信息"""
        data: Dict = {}
        for account_id, account in self.accounts.items():
            data[account_id] = {
                "gateway_name": account.gateway_name,
                "account_name": account.account_name,
                "enabled": account.enabled,
                "max_repay_amount": account.max_repay_amount,
                "min_balance": account.min_balance
            }
        save_json(self.account_filename, data)
    
    def load_tasks(self) -> None:
        """加载任务配置"""
        try:
            data: Dict = load_json(self.task_filename)
        except Exception:
            data = {}
        
        for task_id, task_data in data.items():
            try:
                task = RepayTask()
                task.task_id = task_id
                task.account_id = task_data.get("account_id", "")
                task.task_name = task_data.get("task_name", "")
                
                repay_type_value = task_data.get("repay_type", "定时执行")
                for rt in RepayType:
                    if rt.value == repay_type_value:
                        task.repay_type = rt
                        break
                
                fixed_time_str = task_data.get("fixed_time", "15:30")
                hours, minutes = map(int, fixed_time_str.split(":"))
                task.fixed_time = dt_time(hours, minutes)
                
                task.interval_value = task_data.get("interval_value", 24)
                
                interval_unit_value = task_data.get("interval_unit", "小时")
                for iu in IntervalUnit:
                    if iu.value == interval_unit_value:
                        task.interval_unit = iu
                        break
                
                task.enabled = task_data.get("enabled", True)
                
                last_run_str = task_data.get("last_run_time")
                if last_run_str:
                    task.last_run_time = datetime.fromisoformat(last_run_str)
                
                next_run_str = task_data.get("next_run_time")
                if next_run_str:
                    task.next_run_time = datetime.fromisoformat(next_run_str)
                
                self.tasks[task_id] = task
            except Exception as e:
                self.write_log(f"解析任务失败: {str(e)}")
                continue
    
    def save_tasks(self) -> None:
        """保存任务配置"""
        data: Dict = {}
        for task_id, task in self.tasks.items():
            data[task_id] = {
                "account_id": task.account_id,
                "task_name": task.task_name,
                "repay_type": task.repay_type.value,
                "fixed_time": task.fixed_time.strftime("%H:%M"),
                "interval_value": task.interval_value,
                "interval_unit": task.interval_unit.value,
                "enabled": task.enabled,
                "last_run_time": task.last_run_time.isoformat() if task.last_run_time else None,
                "next_run_time": task.next_run_time.isoformat() if task.next_run_time else None
            }
        save_json(self.task_filename, data)
    
    def load_records(self) -> None:
        """加载执行记录"""
        try:
            data: List = load_json(self.record_filename)
            if not isinstance(data, list):
                data = []
        except Exception as e:
            self.write_log(f"加载记录文件失败: {str(e)}，将创建新文件")
            data = []
        
        for record_data in data:
            try:
                record = RepayRecord()
                record.record_id = record_data.get("record_id", "")
                record.task_id = record_data.get("task_id", "")
                record.task_name = record_data.get("task_name", "")
                record.account_id = record_data.get("account_id", "")
                record.account_name = record_data.get("account_name", "")
                record.gateway_name = record_data.get("gateway_name", "")
                record.execute_time = datetime.fromisoformat(record_data.get("execute_time", datetime.now().isoformat()))
                record.repay_amount = record_data.get("repay_amount", 0.0)
                record.balance_before = record_data.get("balance_before", 0.0)
                record.balance_after = record_data.get("balance_after", 0.0)
                record.margin_loan_before = record_data.get("margin_loan_before", 0.0)
                record.margin_loan_after = record_data.get("margin_loan_after", 0.0)
                
                status_value = record_data.get("status", "待执行")
                for rs in RepayStatus:
                    if rs.value == status_value:
                        record.status = rs
                        break
                
                record.error_message = record_data.get("error_message", "")
                self.records.append(record)
            except Exception as e:
                self.write_log(f"解析记录失败: {str(e)}")
                continue
        
        # 按执行时间排序，只保留最近1000条记录
        self.records.sort(key=lambda x: x.execute_time, reverse=True)
        self.records = self.records[:1000]
    
    def save_records(self) -> None:
        """保存执行记录"""
        data: List = []
        for record in self.records:
            data.append({
                "record_id": record.record_id,
                "task_id": record.task_id,
                "task_name": record.task_name,
                "account_id": record.account_id,
                "account_name": record.account_name,
                "gateway_name": record.gateway_name,
                "execute_time": record.execute_time.isoformat(),
                "repay_amount": record.repay_amount,
                "balance_before": record.balance_before,
                "balance_after": record.balance_after,
                "margin_loan_before": record.margin_loan_before,
                "margin_loan_after": record.margin_loan_after,
                "status": record.status.value,
                "error_message": record.error_message
            })
        save_json(self.record_filename, data)
    
    def encrypt(self, text: str) -> str:
        """简单加密（实际生产环境应使用更安全的加密方式）"""
        if not text:
            return ""
        key = "vnpy_autorepay_key_2024"
        encrypted = []
        for i, char in enumerate(text):
            encrypted_char = chr((ord(char) + ord(key[i % len(key)])) % 256)
            encrypted.append(encrypted_char)
        return "".join(encrypted)
    
    def decrypt(self, text: str) -> str:
        """简单解密"""
        if not text:
            return ""
        key = "vnpy_autorepay_key_2024"
        decrypted = []
        for i, char in enumerate(text):
            decrypted_char = chr((ord(char) - ord(key[i % len(key)])) % 256)
            decrypted.append(decrypted_char)
        return "".join(decrypted)
    
    def add_account(self, account: RepayAccount) -> str:
        """添加账户"""
        # 使用用户输入的 account_id（资金账户号），不做任何转换
        account_id = account.account_id
        self.accounts[account_id] = account
        self.save_accounts()
        self.write_log(f"添加融资账户: {account.account_name}")
        self.put_update_event()
        return account_id
    
    def update_account(self, account: RepayAccount) -> None:
        """更新账户"""
        # 查找旧的 account_id（通过比较账户对象）
        old_account_id = None
        for acc_id, acc in self.accounts.items():
            if acc is account or acc.account_name == account.account_name:
                old_account_id = acc_id
                break
        
        # 如果 account_id 发生变化，需要删除旧的 key
        if old_account_id and old_account_id != account.account_id:
            del self.accounts[old_account_id]
        
        # 使用新的 account_id 作为 key 存储
        self.accounts[account.account_id] = account
        self.save_accounts()
        self.write_log(f"更新融资账户: {account.account_name}")
        self.put_update_event()
    
    def delete_account(self, account_id: str) -> None:
        """删除账户"""
        if account_id in self.accounts:
            account_name = self.accounts[account_id].account_name
            # 删除相关任务
            tasks_to_delete = [t_id for t_id, task in self.tasks.items() if task.account_id == account_id]
            for t_id in tasks_to_delete:
                self.delete_task(t_id)
            
            del self.accounts[account_id]
            self.save_accounts()
            self.write_log(f"删除融资账户: {account_name}")
            self.put_update_event()
    
    def get_account(self, account_id: str) -> Optional[RepayAccount]:
        """获取账户信息"""
        return self.accounts.get(account_id)
    
    def get_all_accounts(self) -> List[RepayAccount]:
        """获取所有账户"""
        return list(self.accounts.values())
    
    def add_task(self, task: RepayTask) -> str:
        """添加还款任务"""
        task.task_id = self.generate_id()
        task.next_run_time = self.calculate_next_run_time(task)
        self.tasks[task.task_id] = task
        self.save_tasks()
        self.write_log(f"添加还款任务: {task.task_name}")
        self.put_update_event()
        return task.task_id
    
    def update_task(self, task: RepayTask) -> None:
        """更新还款任务"""
        if task.task_id in self.tasks:
            task.next_run_time = self.calculate_next_run_time(task)
            self.tasks[task.task_id] = task
            self.save_tasks()
            self.write_log(f"更新还款任务: {task.task_name}")
            self.put_update_event()
    
    def delete_task(self, task_id: str) -> None:
        """删除还款任务"""
        if task_id in self.tasks:
            task_name = self.tasks[task_id].task_name
            del self.tasks[task_id]
            self.save_tasks()
            self.write_log(f"删除还款任务: {task_name}")
            self.put_update_event()
    
    def toggle_task(self, task_id: str) -> None:
        """切换任务启用/禁用状态"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.enabled = not task.enabled
            if task.enabled:
                task.next_run_time = self.calculate_next_run_time(task)
            self.save_tasks()
            self.write_log(f"{'启用' if task.enabled else '禁用'}还款任务: {task.task_name}")
            self.put_update_event()
    
    def get_task(self, task_id: str) -> Optional[RepayTask]:
        """获取任务信息"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[RepayTask]:
        """获取所有任务"""
        return list(self.tasks.values())
    
    def generate_id(self) -> str:
        """生成唯一ID"""
        return hashlib.md5(f"{time.time()}{id(self)}".encode()).hexdigest()[:16]
    
    def is_trading_day(self, date: datetime) -> bool:
        """
        判断是否是交易日
        
        优先使用 xtdata 获取的交易日历，如果不可用则使用周末判断
        
        Args:
            date: 待判断的日期
            
        Returns:
            bool: 是否是交易日
        """
        # 周末不是交易日（周六=5, 周日=6）
        if date.weekday() >= 5:
            return False
        
        # 如果有 xtdata 交易日历缓存，直接查询
        if self.trading_calendar_cache:
            year_str = str(date.year)
            date_str = date.strftime("%Y%m%d")  # 格式: YYYYMMDD
            
            if year_str in self.trading_calendar_cache:
                return date_str in self.trading_calendar_cache[year_str]
            
            # 如果当年不在缓存中，尝试动态获取
            if XT_QMT_AVAILABLE:
                try:
                    start_time = f"{date.year}0101"
                    end_time = f"{date.year}1231"
                    trading_days = xtdata.get_trading_calendar('SH', start_time, end_time)
                    trading_set = set(trading_days)
                    self.trading_calendar_cache[year_str] = trading_set
                    return date_str in trading_set
                except Exception:
                    pass
        
        # 兜底方案：基于简单规则的判断（周末已排除）
        # 注意：这种方法不够准确，建议使用 xtdata 获取准确的交易日历
        return True
    
    def is_trading_time(self, dt: datetime) -> bool:
        """
        判断是否在交易时间内
        
        Args:
            dt: 待判断的时间
            
        Returns:
            bool: 是否在交易时间内（09:00-15:30）
        """
        # 先判断是否是交易日
        if not self.is_trading_day(dt):
            return False
        
        # 定义交易时间段
        trading_start = dt_time(9, 0)
        trading_end = dt_time(15, 30)
        current_time = dt.time()
        
        return trading_start <= current_time <= trading_end
    
    def get_next_trading_day_start(self, dt: datetime) -> datetime:
        """
        获取下一个交易日的起始时间（09:00）
        
        Args:
            dt: 当前时间
            
        Returns:
            datetime: 下一个交易日的09:00时间点
        """
        # 从第二天开始查找
        next_day = dt + timedelta(days=1)
        
        # 最多查找30天（避免无限循环）
        for _ in range(30):
            # 重置到当天的09:00
            next_trading_start = datetime.combine(next_day.date(), dt_time(9, 0))
            
            if self.is_trading_day(next_trading_start):
                return next_trading_start
            
            next_day += timedelta(days=1)
        
        # 如果30天内找不到交易日，返回30天后的周一09:00（兜底方案）
        fallback_day = dt + timedelta(days=30)
        while fallback_day.weekday() >= 5:  # 找到下一个周一
            fallback_day += timedelta(days=1)
        return datetime.combine(fallback_day.date(), dt_time(9, 0))
    
    def adjust_to_trading_time(self, dt: datetime) -> datetime:
        """
        将时间调整到有效的交易时间
        
        Args:
            dt: 待调整的时间
            
        Returns:
            datetime: 调整后的有效交易时间
        """
        # 如果不是交易日，返回下一个交易日的09:00
        if not self.is_trading_day(dt):
            return self.get_next_trading_day_start(dt)
        
        # 定义交易时间段
        trading_start = dt_time(9, 0)
        trading_end = dt_time(15, 30)
        current_time = dt.time()
        
        # 如果时间早于09:00，调整为当天的09:00
        if current_time < trading_start:
            return datetime.combine(dt.date(), trading_start)
        
        # 如果时间晚于15:30，返回下一个交易日的09:00
        if current_time > trading_end:
            return self.get_next_trading_day_start(dt)
        
        # 时间在交易时段内，直接返回
        return dt
    
    def calculate_next_run_time(self, task: RepayTask) -> datetime:
        """
        计算下次执行时间
        
        确保计算出的时间严格限制在交易日的09:00-15:30之间
        
        Args:
            task: 还款任务
            
        Returns:
            datetime: 下次执行时间（在有效交易时段内）
        """
        now = datetime.now()
        
        if task.repay_type == RepayType.FIXED_TIME:
            # 定时执行模式
            today_fixed = datetime.combine(now.date(), task.fixed_time)
            
            # 确保设定时间在交易时段内（09:00-15:30）
            trading_start = dt_time(9, 0)
            trading_end = dt_time(15, 30)
            
            # 如果设定时间早于09:00，调整为09:00
            if task.fixed_time < trading_start:
                adjusted_time = trading_start
            # 如果设定时间晚于15:30，调整为15:30
            elif task.fixed_time > trading_end:
                adjusted_time = trading_end
            else:
                adjusted_time = task.fixed_time
            
            today_adjusted = datetime.combine(now.date(), adjusted_time)
            
            if now < today_adjusted and self.is_trading_day(today_adjusted):
                # 今天还没到设定时间，且今天是交易日
                return today_adjusted
            else:
                # 今天已过设定时间，或今天不是交易日
                # 找下一个交易日
                next_day = now + timedelta(days=1)
                for _ in range(30):  # 最多查找30天
                    next_fixed = datetime.combine(next_day.date(), adjusted_time)
                    if self.is_trading_day(next_fixed):
                        return next_fixed
                    next_day += timedelta(days=1)
                
                # 兜底方案：30天后的周一
                fallback_day = now + timedelta(days=30)
                while fallback_day.weekday() >= 5:
                    fallback_day += timedelta(days=1)
                return datetime.combine(fallback_day.date(), adjusted_time)
        
        else:
            # 间隔执行模式
            if task.last_run_time:
                last_run = task.last_run_time
            else:
                last_run = now
            
            delta = timedelta()
            if task.interval_unit == IntervalUnit.MINUTES:
                delta = timedelta(minutes=task.interval_value)
            elif task.interval_unit == IntervalUnit.HOURS:
                delta = timedelta(hours=task.interval_value)
            elif task.interval_unit == IntervalUnit.DAYS:
                delta = timedelta(days=task.interval_value)
            elif task.interval_unit == IntervalUnit.WEEKS:
                delta = timedelta(weeks=task.interval_value)
            
            # 计算初步的下次执行时间
            next_run = last_run + delta
            
            # 如果计算出的时间已经过去，递增直到找到未来的时间
            if next_run <= now:
                while next_run <= now:
                    next_run += delta
            
            # 调整到有效的交易时间
            adjusted_run = self.adjust_to_trading_time(next_run)
            
            # 如果调整后的时间仍然在过去（极端情况），继续查找下一个有效时间
            if adjusted_run <= now:
                # 从当前时间开始查找下一个交易时段
                adjusted_run = self.adjust_to_trading_time(now + timedelta(minutes=1))
            
            return adjusted_run
    
    def execute_repay(self, task: RepayTask) -> None:
        """执行还款操作"""
        # 立即更新下次执行时间，防止重复触发
        task.next_run_time = self.calculate_next_run_time(task)
        
        record = RepayRecord()
        record.record_id = self.generate_id()
        record.task_id = task.task_id
        record.task_name = task.task_name
        record.account_id = task.account_id
        
        account = self.accounts.get(task.account_id)
        if not account:
            record.status = RepayStatus.FAILED
            record.error_message = "账户不存在"
            self.records.insert(0, record)
            self.save_records()
            self.put_update_event()
            return
        
        record.account_name = account.account_name
        record.gateway_name = account.gateway_name
        
        # 获取账户当前状态
        vt_accountid = f"{account.gateway_name}.{account.account_id}"
        account_data = self.main_engine.get_account(vt_accountid)
        
        if not account_data:
            record.status = RepayStatus.FAILED
            record.error_message = "无法获取账户信息，请先连接交易网关"
            self.records.insert(0, record)
            self.save_records()
            self.put_update_event()
            return
        
        record.balance_before = account_data.balance
        # margin_loan: 用户当前的融资欠款金额（应为非负数值）
        record.margin_loan_before = account_data.margin_loan or 0.0
        
        # 计算可还款金额
        # available: 用户可用于还款的资金金额 = 总资金 - 冻结资金（应为非负数值）
        available_balance = account_data.available - account.min_balance
        if available_balance <= 0:
            record.status = RepayStatus.FAILED
            record.error_message = "可用余额不足（扣除最小保留余额后）"
            record.balance_after = account_data.balance
            record.margin_loan_after = record.margin_loan_before
            self.records.insert(0, record)
            self.save_records()
            self.put_update_event()
            return
        
        # 计算还款金额（不超过欠款和最大还款额）
        repay_amount = min(available_balance, record.margin_loan_before)
        if account.max_repay_amount > 0:
            repay_amount = min(repay_amount, account.max_repay_amount)
        
        if repay_amount <= 0:
            record.status = RepayStatus.FAILED
            record.error_message = "无需还款（无融资负债）"
            record.balance_after = account_data.balance
            record.margin_loan_after = record.margin_loan_before
            self.records.insert(0, record)
            self.save_records()
            self.put_update_event()
            return
        
        record.repay_amount = repay_amount
        
        try:
            task.status = RepayStatus.RUNNING
            self.save_tasks()
            
            success = self.perform_repay(account, repay_amount)
            
            if success:
                record.status = RepayStatus.SUCCESS
                # 还款后：可用资金减少，还款金额增加
                record.balance_after = account_data.balance - repay_amount
                # margin_loan_after: 还款后融资负债 = 原负债 - 还款金额（应为非负数值）
                record.margin_loan_after = max(0, record.margin_loan_before - repay_amount)
                self.write_log(f"还款成功 - 账户: {account.account_name}, 金额: {repay_amount:.2f}")
            else:
                record.status = RepayStatus.FAILED
                record.error_message = "还款操作失败"
                record.balance_after = account_data.balance
                record.margin_loan_after = record.margin_loan_before
                self.write_log(f"还款失败 - 账户: {account.account_name}", level="error")
                
        except Exception as e:
            record.status = RepayStatus.FAILED
            record.error_message = str(e)
            record.balance_after = account_data.balance
            record.margin_loan_after = record.margin_loan_before
            self.write_log(f"还款异常 - 账户: {account.account_name}, 错误: {str(e)}", level="error")
        
        task.last_run_time = datetime.now()
        task.status = record.status
        
        self.records.insert(0, record)
        if len(self.records) > 1000:
            self.records = self.records[:1000]
        
        self.save_records()
        self.save_tasks()
        self.put_update_event()
    
    def perform_repay(self, account: RepayAccount, amount: float) -> bool:
        """
        执行实际还款操作
        
        通过gateway调用融资账户的现金还款接口
        
        Args:
            account: 融资账户
            amount: 还款金额
            
        Returns:
            bool: 是否成功发送还款委托
        """
        self.write_log(f"执行还款 - 账户: {account.account_name}, 网关: {account.gateway_name}, 金额: {amount:.2f}")
        
        # 获取gateway实例
        gateway = self.main_engine.get_gateway(account.gateway_name)
        
        if not gateway:
            self.write_log(f"无法获取网关 {account.gateway_name}，还款失败", level="error")
            return False
        
        # 获取XtTdApi实例（repay_cash方法在XtTdApi中定义）
        td_api = getattr(gateway, "td_api", None)
        
        if not td_api:
            self.write_log(f"网关 {account.gateway_name} 未初始化交易API，还款失败", level="error")
            return False
        
        # 检查td_api是否有还款接口
        if not hasattr(td_api, "repay_cash"):
            self.write_log(f"网关 {account.gateway_name} 不支持现金还款功能", level="error")
            return False
        
        # 调用XtTdApi的现金还款接口
        try:
            order_id = td_api.repay_cash(amount)
            
            if order_id:
                self.write_log(f"现金还款委托已发送 - 委托号: {order_id}")
                return True
            else:
                self.write_log("现金还款委托发送失败", level="error")
                return False
                
        except Exception as e:
            self.write_log(f"现金还款执行异常: {str(e)}", level="error")
            return False
    
    def get_all_records(self) -> List[RepayRecord]:
        """获取所有执行记录"""
        return self.records
    
    def get_records_by_account(self, account_id: str) -> List[RepayRecord]:
        """按账户获取执行记录"""
        return [r for r in self.records if r.account_id == account_id]
    
    def write_log(self, msg: str, level: str = "info") -> None:
        """写入日志"""
        log = LogData(msg=msg, gateway_name=APP_NAME)
        event = Event(EVENT_AUTOREPAY_LOG, log)
        self.event_engine.put(event)
    
    def put_update_event(self) -> None:
        """推送更新事件"""
        event = Event(EVENT_AUTOREPAY_UPDATE, {})
        self.event_engine.put(event)
    
    def close(self) -> None:
        """关闭引擎"""
        self.write_log("自动还款引擎关闭")
