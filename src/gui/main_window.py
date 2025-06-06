from pathlib import Path
from socket import SocketType
from typing import Optional

from PySide6.QtCore import QEvent, QObject, QRegularExpression, Qt, QTimer, Signal
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

from helpers.constants import IP, PING_INTERVAL, PORT
from helpers.helpers import close_socket, get_root_dir

from ..hvps.hvps_api import HVPSv3
from .hvps_test_window import HVPSTestWindow
from .open_socket_window import OpenSocketWindow


class MainWindow(QMainWindow):
    def __init__(self, version: str, sock: Optional[SocketType] = None) -> None:
        super().__init__()
        self.version = version
        self.ip: str = IP
        self.port: str = str(PORT)
        self.sock: Optional[SocketType] = sock
        self.hvps: HVPSv3

        # If there's a socket connection, instantiate the HVPS object
        # and begin pinging to prevent HVPS from timing out.
        if self.sock:
            self.hvps = HVPSv3(self.sock)
            self.start_pinging_hvps()

        self.installEventFilter(self)
        self.open_socket_window: Optional[OpenSocketWindow] = None
        self.hvps_test_window: Optional[HVPSTestWindow] = None
        self.create_gui()

    def start_pinging_hvps(self) -> None:
        """
        Creates a QTimer to ping the HVPS every
        """
        self.keep_alive_timer = QTimer(self)
        self.keep_alive_timer.timeout.connect(self.handle_hvps_ping)
        self.keep_alive_timer.start(PING_INTERVAL)

    def create_gui(self) -> None:
        window_width = 300
        window_height = 400
        button_width = 75
        self.setFixedSize(window_width, window_height)
        root_dir: Path = get_root_dir()
        icon_path: str = str(root_dir / 'assets' / 'hvps_icon.ico')
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle(f'HVPS Controller (v{self.version})')
        apply_stylesheet(self, theme='dark_lightgreen.xml', invert_secondary=True)
        self.setStyleSheet(
            self.styleSheet() + """QLineEdit, QTextEdit {color: lightgreen;}"""
        )

        self.beam_setting: str = '0'
        self.ext_setting: str = '0'
        self.L1_setting: str = '0'
        self.L2_setting: str = '0'
        self.L3_setting: str = '0'
        self.L4_setting: str = '0'
        self.sol_setting: str = '0'

        voltage_regex = QRegularExpression(r'^-?\d{1,5}$')
        voltage_validator = QRegularExpressionValidator(voltage_regex)
        current_regex = QRegularExpression(r'^\d{0,1}+\.\d{1,2}$')
        current_validator = QRegularExpressionValidator(current_regex)

        # Create the QAction objects for the menus
        self.open_socket_window_action = QAction(text='Connect', parent=self)
        self.open_socket_window_action.triggered.connect(self.handle_open_socket_window)
        self.run_test_action = QAction(text='Run Test', parent=self)
        self.run_test_action.triggered.connect(self.handle_run_test)
        if not self.sock:
            self.run_test_action.setEnabled(False)
        self.exit_action = QAction(text='Exit', parent=self)
        self.exit_action.triggered.connect(self.handle_exit)
        self.open_user_guide_action = QAction(text='User Guide', parent=self)
        self.open_user_guide_action.triggered.connect(self.open_user_guide)

        # Create the menu bar and menu bar selections
        self.menu_bar = self.menuBar()
        self.file_menu = self.menu_bar.addMenu('File')
        self.file_menu.addAction(self.open_socket_window_action)
        self.file_menu.addAction(self.run_test_action)
        self.file_menu.addAction(self.exit_action)
        self.help_menu = self.menu_bar.addMenu('Help')
        self.help_menu.addAction(self.open_user_guide_action)

        ##### Create the widgets #####
        # Create the buttons
        self.hv_enable_btn = QPushButton('OFF')
        self.hv_enable_btn.setCheckable(True)
        self.hv_enable_btn.setFixedWidth(button_width)
        self.hv_enable_btn.clicked.connect(self.handle_hv_enable_btn)
        self.sol_enable_btn = QPushButton('OFF')
        self.sol_enable_btn.setCheckable(True)
        self.sol_enable_btn.setFixedWidth(button_width)
        self.sol_enable_btn.clicked.connect(self.handle_sol_enable_btn)
        if not self.sock:
            self.hv_enable_btn.setEnabled(False)
            self.sol_enable_btn.setEnabled(False)

        # Create the labels and entry boxes
        self.hv_btn_label = QLabel('High Voltage')
        self.sol_btn_label = QLabel('Solenoid Current')
        self.beam_label = QLabel('Beam')
        self.ext_label = QLabel('Extractor')
        self.L1_label = QLabel('Lens 1')
        self.L2_label = QLabel('Lens 2')
        self.L3_label = QLabel('Lens 3')
        self.L4_label = QLabel('Lens 4')
        self.solenoid_label = QLabel('Solenoid')

        self.beam_entry = QLineEdit(self.beam_setting)
        self.beam_entry.setValidator(voltage_validator)
        self.ext_entry = QLineEdit(self.ext_setting)
        self.ext_entry.setValidator(voltage_validator)
        self.L1_entry = QLineEdit(self.L1_setting)
        self.L1_entry.setValidator(voltage_validator)
        self.L2_entry = QLineEdit(self.L2_setting)
        self.L2_entry.setValidator(voltage_validator)
        self.L3_entry = QLineEdit(self.L3_setting)
        self.L3_entry.setValidator(voltage_validator)
        self.L4_entry = QLineEdit(self.L4_setting)
        self.L4_entry.setValidator(voltage_validator)
        self.solenoid_entry = QLineEdit(self.sol_setting)
        self.solenoid_entry.setValidator(current_validator)

        # Group voltage entries
        self.voltage_entries: dict[QLineEdit, str] = {
            self.beam_entry: self.beam_setting,
            self.ext_entry: self.ext_setting,
            self.L1_entry: self.L1_setting,
            self.L2_entry: self.L2_setting,
            self.L3_entry: self.L3_setting,
            self.L4_entry: self.L4_setting,
        }

        # Set the layout
        btn_layout = QGridLayout()
        btn_layout.addWidget(self.hv_btn_label, 0, 0, Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(self.sol_btn_label, 0, 1, Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(self.hv_enable_btn, 1, 0, Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(self.sol_enable_btn, 1, 1, Qt.AlignmentFlag.AlignCenter)

        label_layout = QVBoxLayout()
        label_layout.addWidget(self.beam_label)
        label_layout.addWidget(self.ext_label)
        label_layout.addWidget(self.L1_label)
        label_layout.addWidget(self.L2_label)
        label_layout.addWidget(self.L3_label)
        label_layout.addWidget(self.L4_label)
        label_layout.addWidget(self.solenoid_label)

        entry_layout = QVBoxLayout()
        entry_layout.addWidget(self.beam_entry)
        entry_layout.addWidget(self.ext_entry)
        entry_layout.addWidget(self.L1_entry)
        entry_layout.addWidget(self.L2_entry)
        entry_layout.addWidget(self.L3_entry)
        entry_layout.addWidget(self.L4_entry)
        entry_layout.addWidget(self.solenoid_entry)

        main_layout = QGridLayout()
        main_layout.addLayout(btn_layout, 0, 0, 1, 2)
        main_layout.addWidget(QLabel(), 1, 0, 1, 2)  # spacer
        main_layout.addLayout(label_layout, 2, 0)
        main_layout.addLayout(entry_layout, 2, 1)

        container = QWidget()
        container.setLayout(main_layout)

        self.setCentralWidget(container)

    def handle_open_socket_window(self) -> None:
        """
        Opens a window with `IP` and `PORT` QLineEdits and a `Connect` QPushButton,
        populated with IP and PORT global variables.
        If self.sock is not None, all QWidgets in OpenSocketWindow are disabled.
        """
        if self.open_socket_window is None:
            self.open_socket_window = OpenSocketWindow(
                sock=self.sock, parent=self, ip_str=self.ip, port_str=self.port
            )
            self.open_socket_window.successful.connect(self.get_socket)
            self.open_socket_window.closed_window.connect(
                self.handle_connection_window_closed
            )
            self.open_socket_window.show()
            self.open_socket_window.activateWindow()  # gives the window focus
            self.open_socket_window.raise_()  # ensures window is visually on top of other windows

    def get_socket(self, sock: SocketType) -> None:
        """
        Gets the socket from the OpenSocketWindow Signal.
        Instatiates the HVPSv3 class with the socket connection.
        Begins the ping timer so HVPS does not timeout the connection.
        Enables the HV and Solenoid buttons in the gui.
        """
        self.sock = sock
        self.hvps = HVPSv3(self.sock)
        self.start_pinging_hvps()
        self.run_test_action.setEnabled(True)
        self.hv_enable_btn.setEnabled(True)
        self.sol_enable_btn.setEnabled(True)

    def handle_connection_window_closed(self, ip: str, port: str) -> None:
        """
        Sets the open_socket_window object to None for clean up purposes.
        Sets self.ip and self.port to the user inputs
        """
        self.open_socket_window = None
        self.ip = ip
        self.port = port

    def handle_run_test(self) -> None:
        if self.hvps_test_window is None and self.sock is not None:
            self.hvps_test_window = HVPSTestWindow(sock=self.sock, parent=self)
            self.hvps_test_window.test_complete.connect(self.handle_hvps_test_complete)
            self.hvps_test_window.window_closed.connect(
                self.handle_test_hvps_window_closed
            )
            self.hvps_test_window.exec()

    def handle_hvps_test_complete(self) -> None:
        title = 'Test Complete'
        text = 'HVPS test complete'
        buttons = QMessageBox.StandardButton.Ok
        QMessageBox.information(self, title, text, buttons)

    def handle_test_hvps_window_closed(self) -> None:
        self.hvps_test_window = None
        print(f'{self.hvps_test_window = }')

    def handle_exit(self) -> None:
        """
        Quits the application
        """
        QApplication.quit()

    def open_user_guide(self) -> None:
        """
        Open the user guide HTML
        """
        print(get_root_dir())

    def handle_hv_enable_btn(self) -> None:
        """
        Disables HV if the button has been checked.
        Enables HV if the button has not been checked.
        """
        if not self.hv_enable_btn.isChecked():
            self.hv_enable_btn.setText('OFF')
            self.hvps.disable_high_voltage()
        else:
            self.hv_enable_btn.setText('ON')
            self.hvps.enable_high_voltage()
            for (line_edit, setting), channel in zip(
                self.voltage_entries.items(), self.hvps.occupied_channels
            ):
                setting = line_edit.text()
                self.hvps.set_voltage(channel, setting)

    def handle_sol_enable_btn(self) -> None:
        """
        Disables solenoid current if the button has been checked.
        Enables solenoid current if the button has been checked.
        """
        if not self.sol_enable_btn.isChecked():
            self.sol_enable_btn.setText('OFF')
            self.hvps.disable_solenoid_current()
        else:
            self.sol_enable_btn.setText('ON')
            self.sol_setting = self.solenoid_entry.text()
            self.hvps.enable_solenoid_current()
            self.hvps.set_solenoid_current(self.sol_setting)

    def handle_hvps_ping(self) -> None:
        connected: bool = self.hvps.keep_alive()
        if not connected:
            self.run_test_action.setEnabled(False)
            self.hv_enable_btn.setEnabled(False)
            self.sol_enable_btn.setEnabled(False)
            self.sock = None
            self.keep_alive_timer.stop()

    def closeEvent(self, event) -> None:
        """
        Handles what happens when the application is closed.
        If there is socket connection, terminate the connection.
        """
        if self.sock:
            close_socket(self.sock)
        super().closeEvent(event)
