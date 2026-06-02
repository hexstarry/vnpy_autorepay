"""
UI Widgets for vnpy_autorepay
自动还款应用的图形用户界面
"""

from datetime import datetime, time as dt_time
from typing import Optional, List

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import MainEngine, LogData
from vnpy.trader.ui import QtWidgets, QtCore

from ..engine import (
    AutorepayEngine,
    RepayAccount,
    RepayTask,
    RepayRecord,
    APP_NAME,
    EVENT_AUTOREPAY_LOG,
    EVENT_AUTOREPAY_UPDATE,
    RepayStatus,
    RepayType,
    IntervalUnit
)


class AccountManager(QtWidgets.QWidget):
    """账户管理控件"""
    
    def __init__(self, engine: AutorepayEngine):
        super().__init__()
        self.engine: AutorepayEngine = engine
        
        self.current_account: Optional[RepayAccount] = None
        self.init_ui()
        self.update_account_list()
    
    def init_ui(self):
        """初始化界面"""
        layout = QtWidgets.QHBoxLayout()
        
        # 左侧账户列表
        self.account_list = QtWidgets.QListWidget()
        self.account_list.setMaximumWidth(200)
        self.account_list.itemClicked.connect(self.on_account_select)
        layout.addWidget(self.account_list)
        
        # 右侧表单
        form_layout = QtWidgets.QFormLayout()
        
        self.account_name_edit = QtWidgets.QLineEdit()
        form_layout.addRow("账户名称:", self.account_name_edit)
        
        self.gateway_combo = QtWidgets.QComboBox()
        form_layout.addRow("交易网关:", self.gateway_combo)
        
        self.username_edit = QtWidgets.QLineEdit()
        form_layout.addRow("用户名:", self.username_edit)
        
        self.password_edit = QtWidgets.QLineEdit()
        self.password_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        form_layout.addRow("密码:", self.password_edit)
        
        self.max_repay_edit = QtWidgets.QDoubleSpinBox()
        self.max_repay_edit.setRange(0, 100000000)
        self.max_repay_edit.setDecimals(2)
        form_layout.addRow("最大还款金额:", self.max_repay_edit)
        
        self.min_balance_edit = QtWidgets.QDoubleSpinBox()
        self.min_balance_edit.setRange(0, 1000000)
        self.min_balance_edit.setDecimals(2)
        self.min_balance_edit.setValue(1000.0)
        form_layout.addRow("最小保留余额:", self.min_balance_edit)
        
        self.enabled_check = QtWidgets.QCheckBox()
        self.enabled_check.setChecked(True)
        form_layout.addRow("启用:", self.enabled_check)
        
        # 按钮
        button_layout = QtWidgets.QHBoxLayout()
        
        self.add_button = QtWidgets.QPushButton("添加")
        self.add_button.clicked.connect(self.on_add_account)
        button_layout.addWidget(self.add_button)
        
        self.save_button = QtWidgets.QPushButton("保存")
        self.save_button.clicked.connect(self.on_save_account)
        button_layout.addWidget(self.save_button)
        
        self.delete_button = QtWidgets.QPushButton("删除")
        self.delete_button.clicked.connect(self.on_delete_account)
        button_layout.addWidget(self.delete_button)
        
        form_layout.addRow(button_layout)
        
        widget = QtWidgets.QWidget()
        widget.setLayout(form_layout)
        layout.addWidget(widget)
        
        self.setLayout(layout)
        self.load_gateways()
    
    def load_gateways(self):
        """加载可用网关列表"""
        gateways = self.engine.main_engine.get_all_gateway_names()
        self.gateway_combo.addItems(gateways)
    
    def update_account_list(self):
        """更新账户列表"""
        self.account_list.clear()
        accounts = self.engine.get_all_accounts()
        
        for account in accounts:
            item = QtWidgets.QListWidgetItem(f"{account.account_name} ({account.gateway_name})")
            item.setData(QtCore.Qt.ItemDataRole.UserRole, account.account_id)
            self.account_list.addItem(item)
    
    def on_account_select(self, item: QtWidgets.QListWidgetItem):
        """选择账户"""
        account_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        self.current_account = self.engine.get_account(account_id)
        
        if self.current_account:
            self.account_name_edit.setText(self.current_account.account_name)
            self.gateway_combo.setCurrentText(self.current_account.gateway_name)
            self.username_edit.setText(self.current_account.username)
            self.password_edit.setText(self.current_account.password)
            self.max_repay_edit.setValue(self.current_account.max_repay_amount)
            self.min_balance_edit.setValue(self.current_account.min_balance)
            self.enabled_check.setChecked(self.current_account.enabled)
    
    def on_add_account(self):
        """添加账户"""
        account = RepayAccount()
        account.account_name = self.account_name_edit.text()
        account.gateway_name = self.gateway_combo.currentText()
        account.username = self.username_edit.text()
        account.password = self.password_edit.text()
        account.max_repay_amount = self.max_repay_edit.value()
        account.min_balance = self.min_balance_edit.value()
        account.enabled = self.enabled_check.isChecked()
        
        if not account.account_name:
            QtWidgets.QMessageBox.warning(self, "错误", "请输入账户名称")
            return
        
        if not account.gateway_name:
            QtWidgets.QMessageBox.warning(self, "错误", "请选择交易网关")
            return
        
        self.engine.add_account(account)
        self.update_account_list()
        self.clear_form()
    
    def on_save_account(self):
        """保存账户"""
        if not self.current_account:
            QtWidgets.QMessageBox.warning(self, "错误", "请先选择账户")
            return
        
        self.current_account.account_name = self.account_name_edit.text()
        self.current_account.gateway_name = self.gateway_combo.currentText()
        self.current_account.username = self.username_edit.text()
        self.current_account.password = self.password_edit.text()
        self.current_account.max_repay_amount = self.max_repay_edit.value()
        self.current_account.min_balance = self.min_balance_edit.value()
        self.current_account.enabled = self.enabled_check.isChecked()
        
        self.engine.update_account(self.current_account)
        self.update_account_list()
    
    def on_delete_account(self):
        """删除账户"""
        if not self.current_account:
            QtWidgets.QMessageBox.warning(self, "错误", "请先选择账户")
            return
        
        reply = QtWidgets.QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除账户 {self.current_account.account_name} 吗？",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.engine.delete_account(self.current_account.account_id)
            self.current_account = None
            self.clear_form()
            self.update_account_list()
    
    def clear_form(self):
        """清空表单"""
        self.account_name_edit.clear()
        self.username_edit.clear()
        self.password_edit.clear()
        self.max_repay_edit.setValue(0)
        self.min_balance_edit.setValue(1000.0)
        self.enabled_check.setChecked(True)


class TaskManager(QtWidgets.QWidget):
    """任务管理控件"""
    
    signal: QtCore.Signal = QtCore.Signal(Event)
    
    def __init__(self, engine: AutorepayEngine, event_engine: EventEngine):
        super().__init__()
        self.engine: AutorepayEngine = engine
        self.event_engine: EventEngine = event_engine
        
        self.current_task: Optional[RepayTask] = None
        self.init_ui()
        self.update_task_list()
        self.register_event()
    
    def init_ui(self):
        """初始化界面"""
        layout = QtWidgets.QHBoxLayout()
        
        # 左侧任务列表
        self.task_list = QtWidgets.QListWidget()
        self.task_list.setMaximumWidth(250)
        self.task_list.itemClicked.connect(self.on_task_select)
        layout.addWidget(self.task_list)
        
        # 右侧表单
        form_layout = QtWidgets.QFormLayout()
        
        self.task_name_edit = QtWidgets.QLineEdit()
        form_layout.addRow("任务名称:", self.task_name_edit)
        
        self.account_combo = QtWidgets.QComboBox()
        form_layout.addRow("关联账户:", self.account_combo)
        
        self.repay_type_combo = QtWidgets.QComboBox()
        self.repay_type_combo.addItems([t.value for t in RepayType])
        self.repay_type_combo.currentIndexChanged.connect(self.on_repay_type_changed)
        form_layout.addRow("触发方式:", self.repay_type_combo)
        
        # 定时设置
        self.time_group = QtWidgets.QGroupBox("定时设置")
        time_layout = QtWidgets.QHBoxLayout()
        self.hour_spin = QtWidgets.QSpinBox()
        self.hour_spin.setRange(0, 23)
        time_layout.addWidget(self.hour_spin)
        time_layout.addWidget(QtWidgets.QLabel(":"))
        self.minute_spin = QtWidgets.QSpinBox()
        self.minute_spin.setRange(0, 59)
        time_layout.addWidget(self.minute_spin)
        self.time_group.setLayout(time_layout)
        form_layout.addRow(self.time_group)
        
        # 间隔设置
        self.interval_group = QtWidgets.QGroupBox("间隔设置")
        interval_layout = QtWidgets.QHBoxLayout()
        self.interval_value_spin = QtWidgets.QSpinBox()
        self.interval_value_spin.setRange(1, 10080)
        interval_layout.addWidget(self.interval_value_spin)
        self.interval_unit_combo = QtWidgets.QComboBox()
        self.interval_unit_combo.addItems([u.value for u in IntervalUnit])
        interval_layout.addWidget(self.interval_unit_combo)
        self.interval_group.setLayout(interval_layout)
        form_layout.addRow(self.interval_group)
        
        self.enabled_check = QtWidgets.QCheckBox()
        self.enabled_check.setChecked(True)
        form_layout.addRow("启用:", self.enabled_check)
        
        # 状态信息
        self.last_run_label = QtWidgets.QLabel("上次执行: 从未")
        form_layout.addRow(self.last_run_label)
        
        self.next_run_label = QtWidgets.QLabel("下次执行: ")
        form_layout.addRow(self.next_run_label)
        
        # 按钮
        button_layout = QtWidgets.QHBoxLayout()
        
        self.add_button = QtWidgets.QPushButton("添加")
        self.add_button.clicked.connect(self.on_add_task)
        button_layout.addWidget(self.add_button)
        
        self.save_button = QtWidgets.QPushButton("保存")
        self.save_button.clicked.connect(self.on_save_task)
        button_layout.addWidget(self.save_button)
        
        self.delete_button = QtWidgets.QPushButton("删除")
        self.delete_button.clicked.connect(self.on_delete_task)
        button_layout.addWidget(self.delete_button)
        
        self.execute_now_button = QtWidgets.QPushButton("立即执行")
        self.execute_now_button.clicked.connect(self.on_execute_now)
        button_layout.addWidget(self.execute_now_button)
        
        form_layout.addRow(button_layout)
        
        widget = QtWidgets.QWidget()
        widget.setLayout(form_layout)
        layout.addWidget(widget)
        
        self.setLayout(layout)
        self.load_accounts()
        self.on_repay_type_changed(0)
    
    def load_accounts(self):
        """加载账户列表"""
        self.account_combo.clear()
        accounts = self.engine.get_all_accounts()
        
        for account in accounts:
            self.account_combo.addItem(f"{account.account_name} ({account.gateway_name})", account.account_id)
    
    def register_event(self):
        """注册事件监听"""
        self.signal.connect(self.process_update_event)
        self.event_engine.register(EVENT_AUTOREPAY_UPDATE, self.signal.emit)
    
    def process_update_event(self, event: Event):
        """处理更新事件"""
        self.load_accounts()
        self.update_task_list()
    
    def update_task_list(self):
        """更新任务列表"""
        self.task_list.clear()
        tasks = self.engine.get_all_tasks()
        
        for task in tasks:
            status_icon = "●" if task.enabled else "○"
            item = QtWidgets.QListWidgetItem(f"{status_icon} {task.task_name}")
            item.setData(QtCore.Qt.ItemDataRole.UserRole, task.task_id)
            self.task_list.addItem(item)
    
    def on_repay_type_changed(self, index):
        """切换还款类型"""
        repay_types = list(RepayType)
        repay_type = repay_types[index]
        self.time_group.setVisible(repay_type == RepayType.FIXED_TIME)
        self.interval_group.setVisible(repay_type == RepayType.INTERVAL)
    
    def on_task_select(self, item: QtWidgets.QListWidgetItem):
        """选择任务"""
        task_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        self.current_task = self.engine.get_task(task_id)
        
        if self.current_task:
            self.task_name_edit.setText(self.current_task.task_name)
            self.account_combo.setCurrentIndex(self.account_combo.findData(self.current_task.account_id))
            repay_types = list(RepayType)
            repay_index = repay_types.index(self.current_task.repay_type)
            self.repay_type_combo.setCurrentIndex(repay_index)
            
            self.hour_spin.setValue(self.current_task.fixed_time.hour)
            self.minute_spin.setValue(self.current_task.fixed_time.minute)
            
            self.interval_value_spin.setValue(self.current_task.interval_value)
            interval_units = list(IntervalUnit)
            interval_index = interval_units.index(self.current_task.interval_unit)
            self.interval_unit_combo.setCurrentIndex(interval_index)
            
            self.enabled_check.setChecked(self.current_task.enabled)
            
            if self.current_task.last_run_time:
                self.last_run_label.setText(f"上次执行: {self.current_task.last_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                self.last_run_label.setText("上次执行: 从未")
            
            if self.current_task.next_run_time:
                self.next_run_label.setText(f"下次执行: {self.current_task.next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                self.next_run_label.setText("下次执行: ")
    
    def on_add_task(self):
        """添加任务"""
        task = RepayTask()
        task.task_name = self.task_name_edit.text()
        
        account_id = self.account_combo.currentData()
        if account_id is None:
            QtWidgets.QMessageBox.warning(self, "错误", "请选择关联账户")
            return
        task.account_id = account_id
        
        repay_types = list(RepayType)
        task.repay_type = repay_types[self.repay_type_combo.currentIndex()]
        task.fixed_time = dt_time(self.hour_spin.value(), self.minute_spin.value())
        task.interval_value = self.interval_value_spin.value()
        interval_units = list(IntervalUnit)
        task.interval_unit = interval_units[self.interval_unit_combo.currentIndex()]
        task.enabled = self.enabled_check.isChecked()
        
        if not task.task_name:
            QtWidgets.QMessageBox.warning(self, "错误", "请输入任务名称")
            return
        
        self.engine.add_task(task)
        self.update_task_list()
        self.clear_form()
    
    def on_save_task(self):
        """保存任务"""
        if not self.current_task:
            QtWidgets.QMessageBox.warning(self, "错误", "请先选择任务")
            return
        
        self.current_task.task_name = self.task_name_edit.text()
        
        account_id = self.account_combo.currentData()
        if account_id is not None:
            self.current_task.account_id = account_id
        
        repay_types = list(RepayType)
        self.current_task.repay_type = repay_types[self.repay_type_combo.currentIndex()]
        self.current_task.fixed_time = dt_time(self.hour_spin.value(), self.minute_spin.value())
        self.current_task.interval_value = self.interval_value_spin.value()
        interval_units = list(IntervalUnit)
        self.current_task.interval_unit = interval_units[self.interval_unit_combo.currentIndex()]
        self.current_task.enabled = self.enabled_check.isChecked()
        
        self.engine.update_task(self.current_task)
        self.update_task_list()
    
    def on_delete_task(self):
        """删除任务"""
        if not self.current_task:
            QtWidgets.QMessageBox.warning(self, "错误", "请先选择任务")
            return
        
        reply = QtWidgets.QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除任务 {self.current_task.task_name} 吗？",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.engine.delete_task(self.current_task.task_id)
            self.current_task = None
            self.clear_form()
            self.update_task_list()
    
    def on_execute_now(self):
        """立即执行任务"""
        if not self.current_task:
            QtWidgets.QMessageBox.warning(self, "错误", "请先选择任务")
            return
        
        self.engine.execute_repay(self.current_task)
    
    def clear_form(self):
        """清空表单"""
        self.task_name_edit.clear()
        self.hour_spin.setValue(15)
        self.minute_spin.setValue(30)
        self.interval_value_spin.setValue(24)
        self.interval_unit_combo.setCurrentIndex(1)
        self.enabled_check.setChecked(True)
        self.last_run_label.setText("上次执行: 从未")
        self.next_run_label.setText("下次执行: ")


class RecordMonitor(QtWidgets.QTableWidget):
    """执行记录监控控件"""
    
    signal: QtCore.Signal = QtCore.Signal(Event)
    
    def __init__(self, engine: AutorepayEngine, event_engine: EventEngine):
        super().__init__()
        self.engine: AutorepayEngine = engine
        self.event_engine: EventEngine = event_engine
        
        self.init_ui()
        self.register_event()
        self.update_records()
    
    def init_ui(self):
        """初始化界面"""
        labels = [
            "时间",
            "任务名称",
            "账户名称",
            "网关",
            "还款金额",
            "余额(前)",
            "余额(后)",
            "负债(前)",
            "负债(后)",
            "状态",
            "错误信息"
        ]
        self.setColumnCount(len(labels))
        self.setHorizontalHeaderLabels(labels)
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        
        for i in [0, 1, 2, 3, 9]:
            self.horizontalHeader().setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        
        for i in [4, 5, 6, 7, 8]:
            self.horizontalHeader().setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeMode.Stretch)
        
        self.setWordWrap(True)
    
    def register_event(self):
        """注册事件监听"""
        self.signal.connect(self.process_update_event)
        self.event_engine.register(EVENT_AUTOREPAY_UPDATE, self.signal.emit)
    
    def process_update_event(self, event: Event):
        """处理更新事件"""
        self.update_records()
    
    def update_records(self):
        """更新记录列表"""
        self.clearContents()
        self.setRowCount(0)
        
        records = self.engine.get_all_records()
        
        for record in records:
            row = self.rowCount()
            self.insertRow(row)
            
            self.setItem(row, 0, QtWidgets.QTableWidgetItem(record.execute_time.strftime("%Y-%m-%d %H:%M:%S")))
            self.setItem(row, 1, QtWidgets.QTableWidgetItem(record.task_name))
            self.setItem(row, 2, QtWidgets.QTableWidgetItem(record.account_name))
            self.setItem(row, 3, QtWidgets.QTableWidgetItem(record.gateway_name))
            self.setItem(row, 4, QtWidgets.QTableWidgetItem(f"{record.repay_amount:.2f}"))
            self.setItem(row, 5, QtWidgets.QTableWidgetItem(f"{record.balance_before:.2f}"))
            self.setItem(row, 6, QtWidgets.QTableWidgetItem(f"{record.balance_after:.2f}"))
            self.setItem(row, 7, QtWidgets.QTableWidgetItem(f"{record.margin_loan_before:.2f}"))
            self.setItem(row, 8, QtWidgets.QTableWidgetItem(f"{record.margin_loan_after:.2f}"))
            
            status_item = QtWidgets.QTableWidgetItem(record.status.value)
            if record.status == RepayStatus.SUCCESS:
                status_item.setForeground(QtCore.Qt.GlobalColor.green)
            elif record.status == RepayStatus.FAILED:
                status_item.setForeground(QtCore.Qt.GlobalColor.red)
            elif record.status == RepayStatus.RUNNING:
                status_item.setForeground(QtCore.Qt.GlobalColor.blue)
            self.setItem(row, 9, status_item)
            
            self.setItem(row, 10, QtWidgets.QTableWidgetItem(record.error_message))


class LogMonitor(QtWidgets.QTableWidget):
    """日志监控控件"""
    
    signal: QtCore.Signal = QtCore.Signal(Event)
    
    def __init__(self, event_engine: EventEngine):
        super().__init__()
        self.event_engine: EventEngine = event_engine
        
        self.init_ui()
        self.register_event()
    
    def init_ui(self):
        """初始化界面"""
        labels = ["时间", "信息"]
        self.setColumnCount(len(labels))
        self.setHorizontalHeaderLabels(labels)
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.setWordWrap(True)
    
    def register_event(self):
        """注册事件监听"""
        self.signal.connect(self.process_log_event)
        self.event_engine.register(EVENT_AUTOREPAY_LOG, self.signal.emit)
    
    def process_log_event(self, event: Event):
        """处理日志事件"""
        log: LogData = event.data
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        self.insertRow(0)
        self.setItem(0, 0, QtWidgets.QTableWidgetItem(timestamp))
        self.setItem(0, 1, QtWidgets.QTableWidgetItem(log.msg))
        
        if self.rowCount() > 1000:
            self.removeRow(self.rowCount() - 1)


class AutorepayManager(QtWidgets.QWidget):
    """自动还款管理主控件"""
    
    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        super().__init__()
        
        self.main_engine: MainEngine = main_engine
        self.event_engine: EventEngine = event_engine
        self.engine: AutorepayEngine = main_engine.get_engine(APP_NAME)
        
        self.init_ui()
        self.engine.init_engine()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("自动还款")
        
        # 创建标签页
        tab_widget = QtWidgets.QTabWidget()
        
        # 账户管理标签
        self.account_manager = AccountManager(self.engine)
        tab_widget.addTab(self.account_manager, "账户管理")
        
        # 任务设置标签
        self.task_manager = TaskManager(self.engine, self.event_engine)
        tab_widget.addTab(self.task_manager, "还款设置")
        
        # 任务监控标签
        monitor_layout = QtWidgets.QVBoxLayout()
        
        self.record_monitor = RecordMonitor(self.engine, self.event_engine)
        monitor_layout.addWidget(self.record_monitor)
        
        self.log_monitor = LogMonitor(self.event_engine)
        self.log_monitor.setMaximumHeight(150)
        monitor_layout.addWidget(self.log_monitor)
        
        monitor_widget = QtWidgets.QWidget()
        monitor_widget.setLayout(monitor_layout)
        tab_widget.addTab(monitor_widget, "任务监控")
        
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(tab_widget)
        
        self.setLayout(layout)
    
    def show(self):
        """显示窗口"""
        self.showMaximized()
