from pathlib import Path
from socket import SocketType
from threading import Lock
from typing import Optional

from PySide6.QtCore import (
    QRegularExpression,
    Qt,
    QThread,
    QTimer,
)
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QIcon,
    QRegularExpressionValidator,
)
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from qt_material import apply_stylesheet

from helpers.constants import IP, PORT
from helpers.helpers import close_socket, get_root_dir

from ..gui.channel_selection_window import ChannelSelectionWindow
from ..hvps.hvps_api import HVPSv3
from ..pdf import HVPSReport
from .bg_thread import Worker
from .hvps_test_window import HVPSTestWindow
from .open_socket_window import OpenSocketWindow

# TODO: Figure out why the voltage and current readbacks are having their digits cut off sometimes.


class MainWindow(QMainWindow):
    """
    This MainWindow class serves as the control panel for the HVPSv3. It allows the
    user to enable and disable the high voltage and constant current power supplies,
    enter voltage targets for up to six high voltage channels, and enter a current
    target for the one constant current supply used by the solenoid.

    The File menu has three options: `Connect`, `Run Test`, and  `Exit`. Selecting
    `Connect` will open a dialog window which lets the user attempt to make a socket
    connection to the HVPSv3. Selecting `Run Test` will open up a dialog window that
    will run through testing each of the installed channels of the HVPSv3. Selecting
    `Exit` will close the application.

    The Help menu option has one option: `Open User Guide`. Selecting this option will
    open up an html file in the user's default web browser.

    A background thread runs that gets the voltage and current readbacks from all of
    the channels, once every second.
    """

    def __init__(self, version: str, sock: Optional[SocketType] = None) -> None:
        super().__init__()
        self.installEventFilter(self)
        self.version = version
        self.occupied_channels: list[str] = ['BM', 'EX', 'L1', 'L2', 'L3', 'L4', 'SL']
        self.ip: str = IP
        self.port: str = str(PORT)
        self.sock: Optional[SocketType] = sock
        self.hvps: Optional[HVPSv3] = None
        self.hvps_lock = Lock()
        if self.sock:
            self.hvps = HVPSv3(self.sock)

        # Handle background threading
        self.worker_thread = QThread()
        self.worker = Worker()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.start)
        self.worker.updated.connect(self.update_readings)
        self.worker_thread.start()
        self.worker.stopped.connect(self.on_worker_stopped)
        self._ready_to_quit = False

        # Create the secondary windows attributes
        self.open_socket_window: Optional[OpenSocketWindow] = None
        self.hvps_test_window: Optional[HVPSTestWindow] = None

        # Create the attributes that will hold the voltage readback values
        self.beam_Vreadback: str = '0 V'
        self.ext_Vreadback: str = '0 V'
        self.L1_Vreadback: str = '0 V'
        self.L2_Vreadback: str = '0 V'
        self.L3_Vreadback: str = '0 V'
        self.L4_Vreadback: str = '0 V'
        self.sol_Vreadback: str = '0 V'
        self.voltage_readbacks: tuple[str, ...] = (
            self.beam_Vreadback,
            self.ext_Vreadback,
            self.L1_Vreadback,
            self.L2_Vreadback,
            self.L3_Vreadback,
            self.L4_Vreadback,
            self.sol_Vreadback,
        )

        # Create the attributes that will hold the current readback values
        self.beam_Ireadback: str = '0 uA'
        self.ext_Ireadback: str = '0 uA'
        self.L1_Ireadback: str = '0 uA'
        self.L2_Ireadback: str = '0 uA'
        self.L3_Ireadback: str = '0 uA'
        self.L4_Ireadback: str = '0 uA'
        self.sol_Ireadback: str = '0 A'
        self.current_readbacks: tuple[str, ...] = (
            self.beam_Ireadback,
            self.ext_Ireadback,
            self.L1_Ireadback,
            self.L2_Ireadback,
            self.L3_Ireadback,
            self.L4_Ireadback,
            self.sol_Ireadback,
        )

        # Create the attributes that will hold the channel settings
        self.beam_setting: str = '0'
        self.ext_setting: str = '0'
        self.L1_setting: str = '0'
        self.L2_setting: str = '0'
        self.L3_setting: str = '0'
        self.L4_setting: str = '0'
        self.sol_setting: str = '0'
        self.settings: tuple[str, ...] = (
            self.beam_setting,
            self.ext_setting,
            self.L1_setting,
            self.L2_setting,
            self.L3_setting,
            self.L4_setting,
            self.sol_setting,
        )

        self.create_gui()
        QTimer.singleShot(0, self.open_channel_selection_window)

    def open_channel_selection_window(self) -> None:
        self.channel_selection_window = ChannelSelectionWindow(self)
        self.channel_selection_window.channels_selected.connect(
            self.get_occupied_channels
        )
        self.channel_selection_window.window_closed.connect(
            self.channel_selection_window_closed_event
        )
        self.channel_selection_window.exec()

    def get_occupied_channels(self, occupied_channels: list[str]) -> None:
        self.occupied_channels = occupied_channels

    def channel_selection_window_closed_event(self) -> None:
        print('Channel Selection Window Closed')
        print(f'{self.occupied_channels = }')

    def update_readings(self) -> None:
        """
        Updates the QLabels to show the readback values from the HVPS.
        """

        # Return if self.hvps is None
        if not self.hvps:
            return

        # Get the voltage and current readbacks from the HVPSv3 and set the QLabel
        # text in the gui.
        with self.hvps_lock:
            for (
                channel,
                v_readback,
                i_readback,
                v_readback_label,
                i_readback_label,
            ) in zip(
                self.hvps.all_channels,
                self.voltage_readbacks,
                self.current_readbacks,
                self.Vreadback_labels,
                self.Ireadback_labels,
            ):
                # Get the voltage and current readbacks from the HVPS
                v_readback = self.hvps.get_voltage(channel).strip(f'{channel}V ')
                i_readback = self.hvps.get_current(channel).strip(f'{channel}C ')

                i_readback = float(i_readback)

                if channel != 'SL':
                    v_readback = int(v_readback)
                    v_readback_label.setText(f'{v_readback} V')
                    i_readback_label.setText(f'{i_readback:.2f} uA')
                else:
                    v_readback = float(v_readback)
                    v_readback_label.setText(f'{v_readback:.2f} V')
                    i_readback_label.setText(f'{i_readback:.2f} A')

    def create_gui(self) -> None:
        window_width = 330
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

        # Create the validators used for voltage and current entries
        voltage_regex = QRegularExpression(r'^-?\d{1,5}$')
        voltage_validator = QRegularExpressionValidator(voltage_regex)
        current_regex = QRegularExpression(r'^(\d+)?(\.\d{1,2})?$')
        current_validator = QRegularExpressionValidator(current_regex)

        # Create the QAction objects for the menus
        self.open_socket_window_action = QAction(text='Connect', parent=self)
        self.run_test_action = QAction(text='Run Test', parent=self)
        self.exit_action = QAction(text='Exit', parent=self)
        self.open_user_guide_action = QAction(text='User Guide', parent=self)

        # Connect the QActions to slots when triggered
        self.open_socket_window_action.triggered.connect(self.handle_open_socket_window)
        self.run_test_action.triggered.connect(self.handle_run_test)
        self.exit_action.triggered.connect(self.handle_exit)
        self.open_user_guide_action.triggered.connect(self.open_user_guide)

        # Create the menu bar and menu bar selections
        self.menu_bar = self.menuBar()
        self.file_menu = self.menu_bar.addMenu('File')
        self.help_menu = self.menu_bar.addMenu('Help')

        # Add the QActions to the menu bar options
        self.file_menu.addAction(self.open_socket_window_action)
        self.file_menu.addAction(self.run_test_action)
        self.file_menu.addAction(self.exit_action)
        self.help_menu.addAction(self.open_user_guide_action)

        ##### Create the widgets #####
        # Create the enable buttons
        self.hv_enable_btn = QPushButton('OFF')
        self.sol_enable_btn = QPushButton('OFF')

        # Set the enable buttons to be checkable so they have two states
        self.hv_enable_btn.setCheckable(True)
        self.sol_enable_btn.setCheckable(True)

        # Connect the enable buttons to their handlers
        self.hv_enable_btn.clicked.connect(self.handle_hv_enable_btn)
        self.sol_enable_btn.clicked.connect(self.handle_sol_enable_btn)

        # Set the widths of the buttons
        self.hv_enable_btn.setFixedWidth(button_width)
        self.sol_enable_btn.setFixedWidth(button_width)

        # If a socket connection was not made upon opening, disable the buttons
        if not self.sock:
            self.hv_enable_btn.setEnabled(False)
            self.sol_enable_btn.setEnabled(False)
            self.run_test_action.setEnabled(False)

        # Create the Qlabels
        self.hv_btn_label = QLabel('High Voltage')
        self.sol_btn_label = QLabel('Solenoid Current')
        self.beam_label = QLabel('Beam')
        self.ext_label = QLabel('Extractor')
        self.L1_label = QLabel('Lens 1')
        self.L2_label = QLabel('Lens 2')
        self.L3_label = QLabel('Lens 3')
        self.L4_label = QLabel('Lens 4')
        self.solenoid_label = QLabel('Solenoid')
        self.setting_title_label = QLabel('Setting')
        self.V_readback_title_label = QLabel('Voltage')
        self.I_readback_title_label = QLabel('Current')

        # Create the QLineEdits for the target entries
        self.beam_entry = QLineEdit(self.beam_setting)
        self.ext_entry = QLineEdit(self.ext_setting)
        self.L1_entry = QLineEdit(self.L1_setting)
        self.L2_entry = QLineEdit(self.L2_setting)
        self.L3_entry = QLineEdit(self.L3_setting)
        self.L4_entry = QLineEdit(self.L4_setting)
        self.sol_entry = QLineEdit(self.sol_setting)
        self.entries: tuple[QLineEdit, ...] = (
            self.beam_entry,
            self.ext_entry,
            self.L1_entry,
            self.L2_entry,
            self.L3_entry,
            self.L4_entry,
            self.sol_entry,
        )
        if not self.sock:
            self.enable_entries(False)

        # Set the validators for the QLineEdits so only valid entries are accepted
        self.beam_entry.setValidator(voltage_validator)
        self.ext_entry.setValidator(voltage_validator)
        self.L1_entry.setValidator(voltage_validator)
        self.L2_entry.setValidator(voltage_validator)
        self.L3_entry.setValidator(voltage_validator)
        self.L4_entry.setValidator(voltage_validator)
        self.sol_entry.setValidator(current_validator)

        # Create the QLabels for holding the readback data
        self.beam_Vreadback_label = QLabel(self.beam_Vreadback)
        self.ext_Vreadback_label = QLabel(self.ext_Vreadback)
        self.L1_Vreadback_label = QLabel(self.L1_Vreadback)
        self.L2_Vreadback_label = QLabel(self.L2_Vreadback)
        self.L3_Vreadback_label = QLabel(self.L3_Vreadback)
        self.L4_Vreadback_label = QLabel(self.L4_Vreadback)
        self.sol_Vreading_label = QLabel(self.sol_Vreadback)
        self.Vreadback_labels: tuple[QLabel, ...] = (
            self.beam_Vreadback_label,
            self.ext_Vreadback_label,
            self.L1_Vreadback_label,
            self.L2_Vreadback_label,
            self.L3_Vreadback_label,
            self.L4_Vreadback_label,
            self.sol_Vreading_label,
        )

        self.beam_Ireadback_label = QLabel(self.beam_Ireadback)
        self.ext_Ireadback_label = QLabel(self.ext_Ireadback)
        self.L1_Ireadback_label = QLabel(self.L1_Ireadback)
        self.L2_Ireadback_label = QLabel(self.L2_Ireadback)
        self.L3_Ireadback_label = QLabel(self.L3_Ireadback)
        self.L4_Ireadback_label = QLabel(self.L4_Ireadback)
        self.sol_Ireadback_label = QLabel(self.sol_Ireadback)
        self.Ireadback_labels: tuple[QLabel, ...] = (
            self.beam_Ireadback_label,
            self.ext_Ireadback_label,
            self.L1_Ireadback_label,
            self.L2_Ireadback_label,
            self.L3_Ireadback_label,
            self.L4_Ireadback_label,
            self.sol_Ireadback_label,
        )

        # Create a dictionary of only the voltage QLineEdits and their inputs
        # Keys are the QLineEdits. Values are the entries.
        self.voltage_entries: dict[QLineEdit, str] = {
            self.beam_entry: self.beam_setting,
            self.ext_entry: self.ext_setting,
            self.L1_entry: self.L1_setting,
            self.L2_entry: self.L2_setting,
            self.L3_entry: self.L3_setting,
            self.L4_entry: self.L4_setting,
        }

        # Connect the returnPressed Signal to the handle_return_pressed slot
        # to clear the focus and set the target voltage or current value.
        for entry in self.entries:
            entry.returnPressed.connect(self.handle_return_pressed)

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
        entry_layout.addWidget(self.sol_entry)

        voltage_readback_layout = QVBoxLayout()
        voltage_readback_layout.addWidget(
            self.beam_Vreadback_label, alignment=Qt.AlignmentFlag.AlignRight
        )
        voltage_readback_layout.addWidget(
            self.ext_Vreadback_label, alignment=Qt.AlignmentFlag.AlignRight
        )
        voltage_readback_layout.addWidget(
            self.L1_Vreadback_label, alignment=Qt.AlignmentFlag.AlignRight
        )
        voltage_readback_layout.addWidget(
            self.L2_Vreadback_label, alignment=Qt.AlignmentFlag.AlignRight
        )
        voltage_readback_layout.addWidget(
            self.L3_Vreadback_label, alignment=Qt.AlignmentFlag.AlignRight
        )
        voltage_readback_layout.addWidget(
            self.L4_Vreadback_label, alignment=Qt.AlignmentFlag.AlignRight
        )
        voltage_readback_layout.addWidget(
            self.sol_Vreading_label, alignment=Qt.AlignmentFlag.AlignRight
        )

        current_readback_layout = QVBoxLayout()
        current_readback_layout.addWidget(
            self.beam_Ireadback_label, alignment=Qt.AlignmentFlag.AlignRight
        )
        current_readback_layout.addWidget(
            self.ext_Ireadback_label, alignment=Qt.AlignmentFlag.AlignRight
        )
        current_readback_layout.addWidget(
            self.L1_Ireadback_label, alignment=Qt.AlignmentFlag.AlignRight
        )
        current_readback_layout.addWidget(
            self.L2_Ireadback_label, alignment=Qt.AlignmentFlag.AlignRight
        )
        current_readback_layout.addWidget(
            self.L3_Ireadback_label, alignment=Qt.AlignmentFlag.AlignRight
        )
        current_readback_layout.addWidget(
            self.L4_Ireadback_label, alignment=Qt.AlignmentFlag.AlignRight
        )
        current_readback_layout.addWidget(
            self.sol_Ireadback_label, alignment=Qt.AlignmentFlag.AlignRight
        )

        main_layout = QGridLayout()
        main_layout.addLayout(btn_layout, 0, 0, 1, 4)
        main_layout.addWidget(
            QLabel(), 1, 0, 1, 4
        )  # spacer between the buttons and entry boxes/readback
        main_layout.addWidget(
            self.setting_title_label, 2, 1, alignment=Qt.AlignmentFlag.AlignCenter
        )
        main_layout.addWidget(
            self.V_readback_title_label, 2, 2, alignment=Qt.AlignmentFlag.AlignRight
        )
        main_layout.addWidget(
            self.I_readback_title_label, 2, 3, alignment=Qt.AlignmentFlag.AlignRight
        )
        main_layout.addLayout(label_layout, 3, 0)
        main_layout.addLayout(entry_layout, 3, 1)
        main_layout.addLayout(voltage_readback_layout, 3, 2)
        main_layout.addLayout(current_readback_layout, 3, 3)

        container = QWidget()
        container.setLayout(main_layout)

        self.setCentralWidget(container)

    def handle_open_socket_window(self) -> None:
        """
        Opens a window with `IP` and `PORT` QLineEdits, populated with
        `IP` and `PORT` global variables, and a `Connect` QPushButton.
        Note: If self.sock is None, when the window is opened, all QWidgets
        in OpenSocketWindow are disabled.
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
        self.run_test_action.setEnabled(True)
        self.hv_enable_btn.setEnabled(True)
        self.sol_enable_btn.setEnabled(True)
        self.enable_entries(True)

    def handle_connection_window_closed(self, ip: str, port: str) -> None:
        """
        Sets the open_socket_window object to None for clean up purposes.
        Sets self.ip and self.port to the user inputs
        """
        self.open_socket_window = None
        self.ip = ip
        self.port = port

    def handle_run_test(self) -> None:
        """
        Handles what happens when the user selects the "Run Test" option from the File menu.
        If there isn't already a test window open and there is a socket connection,
        Create the HVPSTestWindow object with the socket connection and connect
        the Signals from the HVPSTestWindow to the proper Slots (methods).
        Shows the test window as a modal window to block interaction with the main window.
        """

        if self.hvps is None:
            return

        # Set the target voltages and target solenoid current to zero
        # and update the QLineEdits to reflect this before the test starts
        for channel, setting, entry in zip(
            self.hvps.all_channels, self.settings, self.entries
        ):
            setting = '0'
            if channel != 'SL':
                self.hvps.set_voltage(channel, setting)
            else:
                self.hvps.set_solenoid_current(setting)
            entry.setText(setting)

        # Check that there isn't already a test window open and that there is a socket connection
        # If all ok, then open up the test window.
        if self.hvps_test_window is None and self.sock is not None:
            self.hvps_test_window = HVPSTestWindow(
                hvps=self.hvps,
                occupied_channels=self.occupied_channels,
                hvps_lock=self.hvps_lock,
                parent=self,
            )
            self.hvps_test_window.test_complete.connect(self.handle_hvps_test_complete)
            self.hvps_test_window.window_closed.connect(
                self.handle_test_hvps_window_closed
            )
            self.enable_entries(False)
            self.hvps_test_window.show()

    def enable_entries(self, enable: bool) -> None:
        """
        Enables or disables the QLineEdits used for setting the voltages and solenoid current
        """
        for entry in self.entries:
            entry.setEnabled(enable)

    def handle_hvps_test_complete(
        self,
        occupied_channels: list[str],
        readbacks: dict[str, list[str]],
        measurements: dict[str, list[str]],
    ) -> None:
        """
        Handles what happens when the HVPS test has completes successfully.
        Gets the emitted Signal and sets the variables for occupied_channels,
        test_readbacks, and test_measurements.
        Shows a message box that lets the user know the test is finished
        and asks if they want to print a test report.
        """
        self.occupied_channels = occupied_channels
        self.test_readbacks = readbacks
        self.test_measurements = measurements

        title = 'Test Complete'
        text = 'HVPS test complete.\nWould you like to print a test report?'
        buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        result = QMessageBox.question(self, title, text, buttons)

        if result == QMessageBox.StandardButton.Yes:
            test_report_pdf = HVPSReport(
                serial_number='None',
                occupied_channels=self.occupied_channels,
                readbacks=self.test_readbacks,
                measurements=self.test_measurements,
            )
            test_report_pdf.open()

    def handle_test_hvps_window_closed(self) -> None:
        """
        Handles what happens when the HVPSTestWindow is closed.
        Sets the object variable to None.
        """
        self.hvps_test_window = None
        self.enable_entries(True)

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
        if not self.hvps:
            return

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
        if self.hvps:
            if not self.sol_enable_btn.isChecked():
                self.sol_enable_btn.setText('OFF')
                self.hvps.disable_solenoid_current()
            else:
                self.sol_enable_btn.setText('ON')
                self.sol_setting = self.sol_entry.text()
                self.hvps.enable_solenoid_current()
                self.hvps.set_solenoid_current(self.sol_setting)

    def on_worker_stopped(self) -> None:
        self.worker_thread.quit()
        self.worker_thread.wait()
        self._ready_to_quit = True
        self.close()  # Now close safely

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Handles what happens when the application is closed.
        If there is socket connection, terminate the connection.
        """
        if self._ready_to_quit:
            event.accept()
        else:
            self._ready_to_quit = False
            self.worker.stop_requested.emit()
            event.ignore()  # wait for cleanup
        if self.sock:
            close_socket(self.sock)
        super().closeEvent(event)

    def handle_return_pressed(self) -> None:
        focused_widget = self.focusWidget()

        if not self.hvps:
            focused_widget.clearFocus()
            return

        with self.hvps_lock:
            match focused_widget:
                case self.beam_entry:
                    setting = self.beam_entry.text()
                    self.hvps.set_voltage('BM', setting)
                case self.ext_entry:
                    setting = self.ext_entry.text()
                    self.hvps.set_voltage('EX', setting)
                case self.L1_entry:
                    setting = self.L1_entry.text()
                    self.hvps.set_voltage('L1', setting)
                case self.L2_entry:
                    setting = self.L2_entry.text()
                    self.hvps.set_voltage('L2', setting)
                case self.L3_entry:
                    setting = self.L3_entry.text()
                    self.hvps.set_voltage('L3', setting)
                case self.L4_entry:
                    setting = self.L4_entry.text()
                    self.hvps.set_voltage('L4', setting)
                case self.sol_entry:
                    setting = self.sol_entry.text()
                    self.hvps.set_voltage('SL', setting)

        focused_widget.clearFocus()
