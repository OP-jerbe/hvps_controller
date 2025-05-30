from pathlib import Path
from socket import SocketType
from typing import Optional

from PySide6.QtCore import QEvent, QObject, QRegularExpression, Qt, Signal
from PySide6.QtGui import QAction, QIcon, QMouseEvent, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from qt_material import apply_stylesheet

from helpers.helpers import close_socket, get_root_dir

from .open_socket_window import OpenSocketWindow


class MainWindow(QMainWindow):
    def __init__(self, version: str, sock: Optional[SocketType]) -> None:
        super().__init__()
        self.version = version
        self.sock: Optional[SocketType] = sock
        self.installEventFilter(self)
        self.create_gui()

    def create_gui(self) -> None:
        window_width = 550
        window_height = 500
        self.setFixedSize(window_width, window_height)

        root_dir: Path = get_root_dir()
        icon_path: str = str(root_dir / 'assets' / 'hvps_icon.ico')
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle(f'HVPSv3 Test Controller (v{self.version})')
        apply_stylesheet(self, theme='dark_lightgreen.xml', invert_secondary=True)
        self.setStyleSheet(
            self.styleSheet() + """QLineEdit, QTextEdit {color: lightgreen;}"""
        )

        # Create the QAction objects for the menus
        self.open_socket_window_action = QAction(text='Connect', parent=self)
        self.open_socket_window_action.triggered.connect(self.handle_open_socket_window)
        self.exit_action = QAction(text='Exit', parent=self)
        self.exit_action.triggered.connect(self.handle_exit)
        self.open_user_guide_action = QAction(text='User Guide', parent=self)
        self.open_user_guide_action.triggered.connect(self.open_user_guide)

        # Create the menu bar and menu bar selections
        self.menu_bar = self.menuBar()
        self.file_menu = self.menu_bar.addMenu('File')
        self.file_menu.addAction(self.open_socket_window_action)
        self.file_menu.addAction(self.exit_action)
        self.help_menu = self.menu_bar.addMenu('Help')
        self.help_menu.addAction(self.open_user_guide_action)

        # Create the layout

    def handle_open_socket_window(self) -> None:
        """
        Opens a window with `IP` and `PORT` QLineEdits and a `Connect` button.
        Populate with IP and PORT global variables.
        """
        self.open_socket_window = OpenSocketWindow(self.sock)
        self.open_socket_window.successful.connect(self.get_socket)
        self.open_socket_window.show()

    def get_socket(self, sock: SocketType) -> None:
        self.sock = sock

    def handle_exit(self) -> None:
        if self.sock:
            close_socket(self.sock)
        QApplication.quit()

    def open_user_guide(self) -> None:
        print(get_root_dir())
