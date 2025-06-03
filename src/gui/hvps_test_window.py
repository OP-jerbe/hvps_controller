from pathlib import Path
from socket import SocketType
from typing import Optional

from PySide6.QtCore import QEvent, QObject, QRegularExpression, Qt, Signal
from PySide6.QtGui import QAction, QIcon, QMouseEvent, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
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

from ..hvps.hvps_api import HVPSv3


class HVPSTestWindow(QDialog):
    test_complete = Signal()
    window_closed = Signal()

    def __init__(self, sock: SocketType, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog)
        self.sock = sock
        self.hvps: HVPSv3
        self.installEventFilter(self)
        root_dir: Path = get_root_dir()
        icon_path: str = str(root_dir / 'assets' / 'hvps_icon.ico')
        self.setWindowIcon(QIcon(icon_path))
        apply_stylesheet(self, theme='dark_lightgreen.xml', invert_secondary=True)
        self.setStyleSheet(
            self.styleSheet() + """QLineEdit, QTextEdit {color: lightgreen;}"""
        )
        self.main_layout = QGridLayout()
        self.create_channel_selection_gui()

    def clear_layout(self) -> None:
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        print('Widgets cleared')

    def create_channel_selection_gui(self) -> None:
        window_width = 280
        window_height = 180
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Select Installed Channels')

        self.beam_channel_chbx = QCheckBox('Beam')
        self.beam_channel_chbx.setChecked(True)
        self.ext_channel_chbx = QCheckBox('Extractor')
        self.ext_channel_chbx.setChecked(True)
        self.L1_channel_chbx = QCheckBox('Lens 1')
        self.L1_channel_chbx.setChecked(True)
        self.L2_channel_chbx = QCheckBox('Lens 2')
        self.L3_channel_chbx = QCheckBox('Lens 3')
        self.L4_channel_chbx = QCheckBox('Lens 4')
        self.sol_channel_chbx = QCheckBox('Solenoid')
        self.sol_channel_chbx.setChecked(True)

        self.checkbox_channels: dict[QCheckBox, str] = {
            self.beam_channel_chbx: 'BM',
            self.ext_channel_chbx: 'EX',
            self.L1_channel_chbx: 'L1',
            self.L2_channel_chbx: 'L2',
            self.L3_channel_chbx: 'L3',
            self.L4_channel_chbx: 'L4',
            self.sol_channel_chbx: 'SL',
        }

        self.channel_select_btn = QPushButton('Ok')
        self.channel_select_btn.clicked.connect(self.handle_channel_select)

        self.main_layout.addWidget(self.beam_channel_chbx, 0, 0)
        self.main_layout.addWidget(self.ext_channel_chbx, 1, 0)
        self.main_layout.addWidget(self.L1_channel_chbx, 0, 1)
        self.main_layout.addWidget(self.L2_channel_chbx, 1, 1)
        self.main_layout.addWidget(self.L3_channel_chbx, 0, 2)
        self.main_layout.addWidget(self.L4_channel_chbx, 1, 2)
        self.main_layout.addWidget(self.sol_channel_chbx, 2, 0)
        self.main_layout.addWidget(
            self.channel_select_btn, 3, 0, 1, 3, Qt.AlignmentFlag.AlignCenter
        )

        self.setLayout(self.main_layout)

    def handle_channel_select(self) -> None:
        self.occupied_channels = []
        for chbx, channel in self.checkbox_channels.items():
            if chbx.isChecked():
                self.occupied_channels.append(channel)
        self.test_plan()

    def test_plan(self) -> None:
        if 'BM' in self.occupied_channels:
            self.clear_layout()
            self.create_beam_test_gui()
        if 'Ext' in self.occupied_channels:
            self.clear_layout()
            self.create_ext_test_gui()
        if 'L1' in self.occupied_channels:
            self.clear_layout()
            self.create_L1_test_gui
        if 'L2' in self.occupied_channels:
            self.clear_layout()
            self.create_L2_test_gui
        if 'L3' in self.occupied_channels:
            self.clear_layout()
            self.create_L3_test_gui
        if 'L4' in self.occupied_channels:
            self.clear_layout()
            self.create_L4_test_gui
        if 'SL' in self.occupied_channels:
            self.clear_layout()
            self.create_sol_test_gui

    def handle_next_btn(self) -> None:
        return

    def create_beam_test_gui(self) -> None:
        print('into beam test')
        window_width = 400
        window_height = 400
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Beam Channel Test')

        next_btn = QPushButton('Next')
        next_btn.clicked.connect(self.handle_next_btn)

        self.main_layout.addWidget(next_btn, 0, 0)
        self.setLayout(self.main_layout)

    def create_ext_test_gui(self) -> None:
        window_width = 400
        window_height = 400
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Extractor Channel Test')

    def create_L1_test_gui(self) -> None:
        window_width = 400
        window_height = 400
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Lens 1 Channel Test')

    def create_L2_test_gui(self) -> None:
        window_width = 400
        window_height = 400
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Lens 2 Channel Test')

    def create_L3_test_gui(self) -> None:
        window_width = 400
        window_height = 400
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Lens 3 Channel Test')

    def create_L4_test_gui(self) -> None:
        window_width = 400
        window_height = 400
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Lens 4 Channel Test')

    def create_sol_test_gui(self) -> None:
        window_width = 400
        window_height = 400
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Solenoid Channel Test')

    def closeEvent(self, event) -> None:
        self.window_closed.emit()
        super().closeEvent(event)
