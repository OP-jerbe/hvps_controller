from pathlib import Path

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

from helpers.helpers import get_root_dir


class MainWindow(QMainWindow):
    def __init__(self, version: str) -> None:
        super().__init__()
        self.version = version
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
        self.exit_option = QAction('Exit')
        self.exit_option.triggered.connect(QApplication.quit)
        self.open_user_guide_option = QAction('User Guide')
        self.open_user_guide_option.triggered.connect(self.open_user_guide)

        # Create the menu bar and menu bar selections
        self.menu_bar = self.menuBar()
        self.file_menu = self.menu_bar.addMenu('File')
        self.file_menu.addAction(self.exit_option)
        self.help_menu = self.menu_bar.addMenu('Help')
        self.help_menu.addAction(self.open_user_guide_option)

    def open_user_guide(self) -> None:
        print(get_root_dir())
