import sys
import socket
import webbrowser
import os
import subprocess
import logging

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame,
    QGraphicsDropShadowEffect, QSpacerItem, QSizePolicy, QSystemTrayIcon, QMenu
)
from PyQt6.QtGui import (
    QFont, QIcon, QColor, QPixmap, QCursor, QPainter, QLinearGradient
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QSize, QEasingCurve, QThread, pyqtSignal, QObject, QPoint
)

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 定义资源文件路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(BASE_DIR, 'icons')
IMAGE_DIR = os.path.join(BASE_DIR, 'images')


def resource_path(relative_path: str) -> str:
    """获取资源文件的绝对路径"""
    return os.path.join(BASE_DIR, relative_path)


class ServiceWorker(QObject):
    """服务工作线程,用于启动和停止服务"""
    started = pyqtSignal()
    stopped = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, script_path: str):
        super().__init__()
        self.script_path = script_path
        self.process = None

    def start_service(self):
        """启动服务"""
        try:
            self.process = subprocess.Popen([sys.executable, self.script_path])
            self.started.emit()
            logging.info("Service process started.")
        except Exception as e:
            self.error.emit(str(e))
            logging.error(f"Error starting service: {e}")

    def stop_service(self):
        """停止服务"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait()
                self.stopped.emit()
                logging.info("Service process terminated.")
            except Exception as e:
                self.error.emit(str(e))
                logging.error(f"Error stopping service: {e}")


class ModernGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.service_worker = None
        self.force_quit = False  # 添加一个强制退出标志
        self.init_ui()
        self.setup_tray_icon()  # 添加系统托盘设置

    def init_ui(self):
        self.setWindowTitle('菌种数据库控制中心')
        self.resize(1000, 700)
        self.setMinimumSize(900, 600)
        self.setWindowIcon(QIcon(resource_path(os.path.join(ICON_DIR, 'app_icon.png'))))

        # 去除窗口边框,创建自定义标题栏
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(0)

        # 背景框架
        background_frame = QFrame()
        background_frame.setObjectName("background_frame")
        background_layout = QVBoxLayout(background_frame)
        background_layout.setContentsMargins(0, 0, 0, 0)
        background_layout.setSpacing(0)

        # 设置背景渐变色和阴影效果
        background_frame.setStyleSheet("""
            QFrame#background_frame {
                background-color: qlineargradient(
                    spread:pad, x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2193b0, stop:0.4 #3366cc, stop:1 #6dd5ed
                );
                border-radius: 20px;
                border: 2px solid rgba(255, 255, 255, 0.1);
            }
        """)
        
        # 添加主窗口阴影
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 80))
        background_frame.setGraphicsEffect(shadow)

        # 创建标题栏
        title_bar = self.create_title_bar()
        background_layout.addWidget(title_bar)

        # 创建内容区域
        content_frame = QFrame()
        content_frame.setObjectName("content_frame")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(40, 35, 40, 35)
        content_layout.setSpacing(25)

        # 设置内容区域的样式
        content_frame.setStyleSheet("""
            QFrame#content_frame {
                background-color: rgba(255, 255, 255, 0.92);
                border-bottom-left-radius: 20px;
                border-bottom-right-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
        """)

        # 添加内容
        self.add_content(content_layout)

        background_layout.addWidget(content_frame)
        main_layout.addWidget(background_frame)

        self.setLayout(main_layout)

        # 初始化拖动窗口相关变量
        self.old_pos = self.pos()

    def create_title_bar(self) -> QWidget:
        title_bar = QFrame()
        title_bar.setFixedHeight(55)
        title_bar.setObjectName("title_bar")
        title_bar.setStyleSheet("""
            QFrame#title_bar {
                background-color: transparent;
                border-top-left-radius: 20px;
                border-top-right-radius: 20px;
            }
        """)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(20, 0, 15, 0)

        # 窗口图标
        window_icon = QLabel()
        window_icon.setPixmap(QPixmap(resource_path(os.path.join(ICON_DIR, 'app_icon.png'))).scaled(32, 32,
                                                                                                    Qt.AspectRatioMode.KeepAspectRatio,
                                                                                                    Qt.TransformationMode.SmoothTransformation))
        window_icon.setFixedSize(32, 32)
        title_layout.addWidget(window_icon)

        # 窗口标题
        title_label = QLabel("菌种数据库控制中心")
        title_label.setStyleSheet("color: white; font-size: 22px; font-weight: bold; padding-left: 10px;")
        title_layout.addWidget(title_label)

        title_layout.addStretch()

        # 最小化、最大化、关闭按钮
        button_size = 40
        
        self.minimize_button = QPushButton()
        self.minimize_button.setIcon(QIcon(resource_path(os.path.join(ICON_DIR, 'minimize.png'))))
        self.minimize_button.setFixedSize(button_size, button_size)
        self.minimize_button.setObjectName("title_bar_button")
        self.minimize_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.minimize_button.clicked.connect(self.showMinimized)

        self.maximize_button = QPushButton()
        self.maximize_button.setIcon(QIcon(resource_path(os.path.join(ICON_DIR, 'maximize.png'))))
        self.maximize_button.setFixedSize(button_size, button_size)
        self.maximize_button.setObjectName("title_bar_button")
        self.maximize_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.maximize_button.clicked.connect(self.toggle_max_restore)

        self.close_button = QPushButton()
        self.close_button.setIcon(QIcon(resource_path(os.path.join(ICON_DIR, 'close.png'))))
        self.close_button.setFixedSize(button_size, button_size)
        self.close_button.setObjectName("title_bar_button")
        self.close_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_button.clicked.connect(self.close)

        title_layout.addWidget(self.minimize_button)
        title_layout.addWidget(self.maximize_button)
        title_layout.addWidget(self.close_button)

        # 按钮样式
        title_bar.setStyleSheet("""
            QPushButton#title_bar_button {
                border: none;
                background-color: transparent;
                border-radius: 20px;
                padding: 8px;
            }
            QPushButton#title_bar_button:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
            QPushButton#title_bar_button:pressed {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)

        # 标题栏拖动
        title_bar.mousePressEvent = self.mousePressEvent
        title_bar.mouseMoveEvent = self.mouseMoveEvent

        return title_bar

    def add_content(self, layout):
        # 定义字体和样式
        self.define_fonts_and_styles()

        # 添加标题
        header_label = QLabel('中烟技术中心菌种数据库')
        header_label.setFont(self.font_header)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet("color: #2d3436; margin-top: 10px;")
        layout.addWidget(header_label)

        # 服务控制框架
        service_frame = self.create_frame()
        service_layout = QHBoxLayout(service_frame)
        service_layout.setSpacing(15)
        service_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.service_button = self.create_button(
            '开启服务',
            resource_path(os.path.join(ICON_DIR, 'service_icon.png')),
            self.service_button_style,
            self.toggle_service
        )
        self.service_button.setCheckable(True)
        self.service_button.setMinimumWidth(200)

        self.light_label = QLabel()
        self.light_label.setFixedSize(16, 16)
        self.update_light_color(False)

        service_layout.addWidget(self.service_button)
        service_layout.addWidget(self.light_label)
        layout.addWidget(service_frame)

        # 功能按钮框架
        function_frame = self.create_frame()
        function_layout = QHBoxLayout(function_frame)
        function_layout.setSpacing(60)
        function_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.search_button = self.create_button(
            '数据查询',
            resource_path(os.path.join(ICON_DIR, 'search_icon.png')),
            self.search_button_style,
            self.microbe_search
        )
        self.admin_button = self.create_button(
            '数据管理',
            resource_path(os.path.join(ICON_DIR, 'admin_icon.png')),
            self.admin_button_style,
            self.admin_system
        )

        function_layout.addWidget(self.search_button)
        function_layout.addWidget(self.admin_button)
        layout.addWidget(function_frame)

        # IP地址显示框架
        ip_frame = self.create_frame()
        ip_layout = QVBoxLayout(ip_frame)
        ip_layout.setSpacing(12)  # 增加间距
        ip_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 设置 ip_frame 的固定高度
        ip_frame.setFixedHeight(140)  # 增加高度

        local_ip_label = self.create_label(
            f'<a href="http://127.0.0.1:5001">本机访问IP:<b>127.0.0.1:5001</b></a>',
            self.font_label,
            self.ip_label_style,
            cursor=True
        )
        local_ip_label.setOpenExternalLinks(True)
        local_ip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lan_ip = self.get_lan_ip()
        lan_ip_label = self.create_label(
            f'<a href="http://{lan_ip}:5001">局域网访问IP:<b>{lan_ip}:5001</b></a>',
            self.font_label,
            self.ip_label_style,
            cursor=True
        )
        lan_ip_label.setOpenExternalLinks(True)
        lan_ip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ip_layout.addWidget(local_ip_label)
        ip_layout.addWidget(lan_ip_label)
        layout.addWidget(ip_frame)
        # 添加占位符以调整布局
        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        layout.addItem(spacer)

    def define_fonts_and_styles(self):
        # 字体
        self.font_header = QFont('Microsoft YaHei', 36, QFont.Weight.Bold)
        self.font_button = QFont('Microsoft YaHei', 16)
        self.font_label = QFont('Microsoft YaHei', 14)
        self.font_usage_link = QFont('Microsoft YaHei', 16)

        # 样式模板 - 修改去除不支持的属性
        self.button_style_template = """
        QPushButton {{
            background-color: {bg_color};
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 16px;
            border-radius: 12px;
            min-width: 180px;
        }}
        QPushButton:hover {{
            background-color: {hover_color};
        }}
        QPushButton:pressed {{
            background-color: {pressed_color};
        }}
        """

        # 按钮样式
        self.service_button_style = self.button_style_template.format(
            bg_color='#4CAF50',
            hover_color='#45a049',
            pressed_color='#3d8b40'
        )
        self.search_button_style = self.button_style_template.format(
            bg_color='#2196F3',
            hover_color='#1e88e5',
            pressed_color='#1976d2'
        )
        self.admin_button_style = self.button_style_template.format(
            bg_color='#FF9800',
            hover_color='#f57c00',
            pressed_color='#ef6c00'
        )

        # 其他样式
        self.frame_style = """
            background-color: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.3);
        """
        self.ip_label_style = """
            color: #2d3436;
            padding: 5px;
        """
        self.usage_link_style = """
            color: #2196F3;
            text-decoration: none;
            font-weight: bold;
            padding: 10px;
        """

    def create_frame(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(self.frame_style)
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 30))
        frame.setGraphicsEffect(shadow)
        return frame

    def create_button(
            self, text: str, icon_path: str, style: str, callback
    ) -> QPushButton:
        button = QPushButton(text)
        button.setFont(self.font_button)
        button.setIcon(QIcon(icon_path))
        button.setIconSize(QSize(24, 24))
        button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        button.clicked.connect(callback)
        button.setStyleSheet(style)
        
        # 添加阴影效果 (替代CSS中的box-shadow)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setXOffset(2)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 50))
        button.setGraphicsEffect(shadow)
        
        return button

    def create_label(
            self, text: str, font: QFont, style: str, cursor: bool = False
    ) -> QLabel:
        label = QLabel(text)
        label.setFont(font)
        label.setStyleSheet(style)
        if cursor:
            label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        return label

    def update_light_color(self, service_running: bool):
        if service_running:
            color = '#4CAF50'  # 绿色
        else:
            color = '#f44336'  # 红色
        # 移除不支持的box-shadow属性
        self.light_label.setStyleSheet(f"""
            background-color: {color};
            border-radius: 8px;
            border: 2px solid rgba(255, 255, 255, 0.8);
        """)
        
        # 可以使用QGraphicsDropShadowEffect代替box-shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(color))
        shadow.setOffset(0, 0)
        self.light_label.setGraphicsEffect(shadow)

    def animate_light(self, service_running: bool):
        animation = QPropertyAnimation(self.light_label, b"size")
        animation.setDuration(300)
        animation.setStartValue(self.light_label.size())
        animation.setEndValue(QSize(18, 18) if service_running else QSize(16, 16))
        animation.setEasingCurve(QEasingCurve.Type.OutBounce if service_running else QEasingCurve.Type.InBounce)
        animation.start()

    def toggle_service(self):
        if self.service_button.isChecked():
            self.start_service()
        else:
            self.stop_service()

    def start_service(self):
        self.service_button.setText('服务已开启')
        self.update_light_color(True)
        self.animate_light(True)
        logging.info("Service starting...")

        # 启动服务
        if not self.service_worker:
            self.service_worker = ServiceWorker("app.py")
            self.service_worker.started.connect(self.on_service_started)
            self.service_worker.stopped.connect(self.on_service_stopped)
            self.service_worker.error.connect(self.on_service_error)
            self.service_worker.start_service()
        
        # 更新托盘菜单项状态
        if hasattr(self, 'start_service_action') and hasattr(self, 'stop_service_action'):
            self.start_service_action.setVisible(False)
            self.stop_service_action.setVisible(True)

    def stop_service(self):
        self.service_button.setText('开启服务')
        self.update_light_color(False)
        self.animate_light(False)
        logging.info("Service stopping...")

        # 停止服务
        if self.service_worker:
            self.service_worker.stop_service()
            self.service_worker = None
        
        # 更新托盘菜单项状态
        if hasattr(self, 'start_service_action') and hasattr(self, 'stop_service_action'):
            self.start_service_action.setVisible(True)
            self.stop_service_action.setVisible(False)

    def on_service_started(self):
        logging.info("Service has started.")

    def on_service_stopped(self):
        logging.info("Service has stopped.")

    def on_service_error(self, error_message: str):
        logging.error(f"Service error: {error_message}")

    def microbe_search(self):
        webbrowser.open("http://127.0.0.1:5001")
        logging.info("Microbe search button clicked.")

    def admin_system(self):
        webbrowser.open("http://127.0.0.1:5001/admin")
        logging.info("Admin system button clicked.")

    def get_lan_ip(self) -> str:
        ip = "Unavailable"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception as e:
            logging.error(f"获取局域网IP时出错: {e}")
        finally:
            s.close()
        return ip

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        delta = event.globalPosition().toPoint() - self.old_pos
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_pos = event.globalPosition().toPoint()

    def toggle_max_restore(self):
        if self.isMaximized():
            self.showNormal()
            self.maximize_button.setIcon(QIcon(resource_path(os.path.join(ICON_DIR, 'maximize.png'))))
        else:
            self.showMaximized()
            self.maximize_button.setIcon(QIcon(resource_path(os.path.join(ICON_DIR, 'restore.png'))))

    def setup_tray_icon(self):
        """设置系统托盘图标和菜单"""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(resource_path(os.path.join(ICON_DIR, 'app_icon.png'))))
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        # 添加菜单项
        show_action = tray_menu.addAction("显示窗口")
        show_action.triggered.connect(self.show_window)
        
        # 修改菜单项，分开为开启和关闭两个选项
        self.start_service_action = tray_menu.addAction("开启服务")
        self.start_service_action.triggered.connect(self.start_service_from_tray)
        
        self.stop_service_action = tray_menu.addAction("关闭服务")
        self.stop_service_action.triggered.connect(self.stop_service_from_tray)
        self.stop_service_action.setVisible(False)  # 初始隐藏关闭服务选项
        
        search_action = tray_menu.addAction("微生物搜索")
        search_action.triggered.connect(self.microbe_search)
        
        admin_action = tray_menu.addAction("管理系统")
        admin_action.triggered.connect(self.admin_system)
        
        tray_menu.addSeparator()
        
        # 只保留一个退出选项
        quit_action = tray_menu.addAction("退出应用")
        quit_action.triggered.connect(self.force_quit_application)
        
        # 设置托盘图标菜单
        self.tray_icon.setContextMenu(tray_menu)
        
        # 连接信号和槽
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        # 显示系统托盘图标
        self.tray_icon.show()
        
        # 设置提示
        self.tray_icon.setToolTip("菌种数据库控制中心")
    
    def tray_icon_activated(self, reason):
        """处理托盘图标激活事件"""
        # 在不同平台上，Trigger和DoubleClick的行为可能不同
        if reason == QSystemTrayIcon.ActivationReason.Trigger or reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # 单击或双击托盘图标
            if self.isVisible() and not self.isMinimized():
                self.hide()
            else:
                self.show_window()
    
    def show_window(self):
        """显示窗口并将其置于前台"""
        self.show()  # 先调用show确保窗口可见
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)  # 恢复窗口并激活
        self.raise_()  # 将窗口提升到顶层
        self.activateWindow()  # 激活窗口
    
    def closeEvent(self, event):
        """重写关闭事件处理"""
        # 检查是否是强制退出
        if hasattr(self, 'force_quit') and self.force_quit:
            # 确保服务被停止
            if self.service_worker:
                self.service_worker.stop_service()
                self.service_worker = None
            # 移除系统托盘图标
            if hasattr(self, 'tray_icon'):
                self.tray_icon.hide()
            event.accept()  # 接受关闭事件，完全关闭应用
            return
        
        if self.tray_icon and self.tray_icon.isVisible():
            # 显示通知消息
            self.tray_icon.showMessage(
                "菌种数据库控制中心",
                "应用已最小化到系统托盘。点击托盘图标可以恢复窗口。",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            self.hide()
            event.ignore()  # 忽略关闭事件
        else:
            # 确保服务被停止
            if self.service_worker:
                self.service_worker.stop_service()
                self.service_worker = None
            event.accept()  # 接受关闭事件，完全关闭应用

    # 新增从托盘启动服务的方法
    def start_service_from_tray(self):
        # 设置按钮为选中状态并启动服务
        self.service_button.setChecked(True)
        self.start_service()
        # 更新托盘菜单项可见性
        self.start_service_action.setVisible(False)
        self.stop_service_action.setVisible(True)

    # 新增从托盘停止服务的方法
    def stop_service_from_tray(self):
        # 设置按钮为未选中状态并停止服务
        self.service_button.setChecked(False)
        self.stop_service()
        # 更新托盘菜单项可见性
        self.start_service_action.setVisible(True)
        self.stop_service_action.setVisible(False)

    # 改进force_quit_application方法，确保清理所有资源
    def force_quit_application(self):
        """强制彻底退出应用，不保存到托盘"""
        # 标记为不要保存到托盘
        self.force_quit = True
        # 停止服务
        if self.service_worker:
            try:
                self.service_worker.stop_service()
                self.service_worker = None
            except Exception as e:
                logging.error(f"停止服务时出错: {e}")
        
        # 隐藏托盘图标
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        
        # 关闭应用
        QApplication.quit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 应用程序只能存在一个实例
    try:
        gui = ModernGUI()
        gui.show()
        sys.exit(app.exec())
    except Exception as e:
        logging.error(f"应用程序发生错误: {e}")
        sys.exit(1)