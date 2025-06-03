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

from helpers.constants import TIMEOUT
from helpers.helpers import get_root_dir, open_socket


class OpenSocketWindow(QWidget):
    successful = Signal(SocketType)
    closed_window = Signal(str, str)

    def __init__(
        self, sock: Optional[SocketType], ip_str: str, port_str: str, parent=None
    ) -> None:
        """
        Inherits from the QWidget class but sets the window type to Dialog so that the
        icon appears in the title bar. Inits the connection_successful flag to False.
        Sets the connection parameters (self.sock, self.ip, and self.port) to the
        inputs. Creates the gui and sets the focus to the connect button.
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog)
        self.connection_successful: bool = False
        self.sock: Optional[SocketType] = sock
        self.ip: str = ip_str
        self.port: str = port_str
        self.create_gui()
        self.connect_btn.setFocus()

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
        self.ip_entry = QLineEdit(self.ip)
        self.ip_entry.setValidator(ip_validator)
        self.port_label = QLabel('PORT')
        self.port_entry = QLineEdit(self.port)
        self.port_entry.setValidator(port_validator)
        self.connect_btn = QPushButton('Connect')
        self.connect_btn.clicked.connect(self.handle_open_socket)

        # Disable the buttons and entry boxes if there is already a socket connection.
        if self.sock:
            self.ip_entry.setEnabled(False)
            self.port_entry.setEnabled(False)
            self.connect_btn.setEnabled(False)
            self.connect_btn.setText('Connected')

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
        """
        Trys to make a socket connection to the HVPS and saves the user inputs for the
        ip and port addresses. If the connection is successful, changes the successful
        connection flag to True and closes the window. Otherwise, shows a pop up to let
        the user know the connection attempt was unsuccessful.
        """
        self.sock: Optional[SocketType] = open_socket(
            ip=self.ip_entry.text(),
            port=int(self.port_entry.text()),
            timeout=TIMEOUT,
        )
        self.ip = self.ip_entry.text()
        self.port = self.port_entry.text()
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
        """
        When the window is closed, if the connection was successful emits the Signal
        with the socket object. Regardless of connection, emits the user input IP
        and port addresses.
        """
        if self.connection_successful:
            self.successful.emit(self.sock)
        self.closed_window.emit(self.ip, self.port)
        super().closeEvent(event)
