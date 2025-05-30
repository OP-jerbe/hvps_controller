from pathlib import Path
from socket import SocketType
from typing import Optional

from PySide6.QtCore import QRegularExpression, Qt, Signal
from PySide6.QtGui import QIcon, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from qt_material import apply_stylesheet

from helpers.helpers import get_root_dir, open_socket

IP: str = '169.254.150.189'
PORT: str = '49076'
TIMEOUT: float = 5.0


class OpenSocketWindow(QWidget):
    successful = Signal(SocketType)

    def __init__(self) -> None:
        super().__init__()
        self.connection_successful: bool = False
        self.sock: Optional[SocketType] = None
        self.create_gui()

    def create_gui(self) -> None:
        # Set the window size
        window_width = 300
        window_height = 130
        self.setFixedSize(window_width, window_height)

        # Set the window icon and title
        root_dir: Path = get_root_dir()
        icon_path: str = str(root_dir / 'assets' / 'hvps_icon.ico')
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle('Connect to HVPS')

        # Apply styling
        apply_stylesheet(self, theme='dark_lightgreen.xml', invert_secondary=True)
        self.setStyleSheet(
            self.styleSheet() + """QLineEdit, QTextEdit {color: lightgreen;}"""
        )

        # Create validator for ip and port inputs
        ip_regex = QRegularExpression(r'[0-9.]*')
        ip_validator = QRegularExpressionValidator(ip_regex)
        port_regex = QRegularExpression(r'[0-9]*')
        port_validator = QRegularExpressionValidator(port_regex)

        # Create the widgets
        self.ip_label = QLabel('IP ADDRESS')
        self.ip_entry = QLineEdit(IP)
        self.ip_entry.setValidator(ip_validator)
        self.port_label = QLabel('PORT')
        self.port_entry = QLineEdit(PORT)
        self.port_entry.setValidator(port_validator)
        self.connect_btn = QPushButton('Connect')
        self.connect_btn.clicked.connect(self.handle_open_socket)

        # Set the layout
        main_layout = QVBoxLayout()
        label_layout = QHBoxLayout()
        input_layout = QHBoxLayout()
        label_layout.addWidget(self.ip_label, alignment=Qt.AlignmentFlag.AlignCenter)
        label_layout.addWidget(self.port_label, alignment=Qt.AlignmentFlag.AlignCenter)
        input_layout.addWidget(self.ip_entry)
        input_layout.addWidget(self.port_entry)
        main_layout.addLayout(label_layout)
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.connect_btn)
        self.setLayout(main_layout)

    def handle_open_socket(self) -> None:
        self.sock: Optional[SocketType] = open_socket(
            ip=self.ip_entry.text(),
            port=int(self.port_entry.text()),
            timeout=TIMEOUT,
        )
        if self.sock:
            self.connection_successful = True
            self.close()
        else:
            self.connection_successful = False
            title = 'Connection Unsuccessful'
            text = (
                f'Connection to {self.ip_entry.text()}:{self.port_entry.text()} failed.'
            )
            buttons = QMessageBox.StandardButton.Ok
            QMessageBox.critical(self, title, text, buttons)

    def closeEvent(self, event) -> None:
        if self.connection_successful:
            self.successful.emit(self.sock)
        super().closeEvent(event)
