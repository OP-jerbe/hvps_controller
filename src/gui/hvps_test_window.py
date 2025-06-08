from pathlib import Path
from socket import SocketType
from typing import Callable

from PySide6.QtCore import QRegularExpression, Qt, Signal
from PySide6.QtGui import (
    QIcon,
    QPixmap,
    QRegularExpressionValidator,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)
from qt_material import apply_stylesheet

from helpers.helpers import get_root_dir

from ..hvps.hvps_api import HVPSv3


class HVPSTestWindow(QDialog):
    test_complete = Signal()
    window_closed = Signal()

    def __init__(self, sock: SocketType, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog)
        self.sock = sock
        self.hvps: HVPSv3 = HVPSv3(sock)
        self.test_voltages: tuple[str, ...] = ('100', '500', '1000')  # volts
        self.test_currents: tuple[str, ...] = ('0.3', '1.2', '2.5')  # amps
        self.channel_readbacks: list[str] = []
        self.channel_measurements: list[str] = []
        self.measurements: dict[str, list[str]] = {}
        self.readbacks: dict[str, list[str]] = {}
        self.installEventFilter(self)
        self.root_dir: Path = get_root_dir()
        icon_path: str = str(self.root_dir / 'assets' / 'hvps_icon.ico')
        self.setWindowIcon(QIcon(icon_path))
        apply_stylesheet(self, theme='dark_lightgreen.xml', invert_secondary=True)
        self.setStyleSheet(
            self.styleSheet() + """QLineEdit, QTextEdit {color: lightgreen;}"""
        )
        lv_regex = QRegularExpression(r'^-?\d{0,3}+\.\d{1,1}$')
        hv_regex = QRegularExpression(r'^-?\d{0,4}+\.\d{1,1}$')
        sol_regex = QRegularExpression(r'^\d{0,1}+\.\d{1,2}$')
        self.lv_validator = QRegularExpressionValidator(lv_regex)
        self.hv_validator = QRegularExpressionValidator(hv_regex)
        self.sol_validator = QRegularExpressionValidator(sol_regex)
        self.main_layout = QGridLayout()
        self.create_channel_selection_gui()

    def get_hv_enable_state(self) -> bool:
        state: str = self.hvps.get_state()
        if state == 'STATE0000' or state == 'STATE0010':
            return False
        return True

    def get_sol_enable_state(self) -> bool:
        state: str = self.hvps.get_state()
        if state == 'STATE0000' or state == 'STATE0001':
            return False
        return True

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
        self.occupied_channels: list[str] = []
        for chbx, channel in self.checkbox_channels.items():
            if chbx.isChecked():
                self.occupied_channels.append(channel)
        self.test_plan()

    def test_plan(self) -> None:
        self.test_stages: list[Callable] = []
        if 'BM' in self.occupied_channels:
            self.test_stages.append(self.create_beam_test_gui)
        if 'EX' in self.occupied_channels:
            self.test_stages.append(self.create_ext_test_gui)
        if 'L1' in self.occupied_channels:
            self.test_stages.append(self.create_L1_test_gui)
        if 'L2' in self.occupied_channels:
            self.test_stages.append(self.create_L2_test_gui)
        if 'L3' in self.occupied_channels:
            self.test_stages.append(self.create_L3_test_gui)
        if 'L4' in self.occupied_channels:
            self.test_stages.append(self.create_L4_test_gui)
        if 'SL' in self.occupied_channels:
            self.test_stages.append(self.create_sol_test_gui)
        self.current_stage_index: int = 0
        self.load_current_stage()

    def load_current_stage(self) -> None:
        if self.current_stage_index < len(self.test_stages):
            self.clear_layout()
            self.test_stages[self.current_stage_index]()
        else:
            self.test_complete.emit()
            self.close()

    def handle_next_btn(self) -> None:
        if self.get_hv_enable_state() is True:  # disable btn not pressed
            self.hvps.disable_high_voltage()
            self.hvps.set_voltage(self.channel, '0')
        if self.get_sol_enable_state() is True:  # disable btn not pressed
            self.hvps.disable_solenoid_current()
            self.hvps.set_solenoid_current('0')

        self.measurements[self.channel] = self.channel_measurements
        self.readbacks[self.channel] = self.channel_readbacks
        self.current_stage_index += 1
        self.load_current_stage()

    def create_beam_test_gui(self) -> None:
        window_width = 1150
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Beam Channel Test')
        self.channel = 'BM'
        pos_100V = self.test_voltages[0]
        pos_500V = self.test_voltages[1]
        pos_1kV = self.test_voltages[2]
        neg_100V = f'-{self.test_voltages[0]}'
        neg_500V = f'-{self.test_voltages[1]}'
        neg_1kV = f'-{self.test_voltages[2]}'

        instructions: str = (
            '1. Plug HV pigtail into Beam HV recepticle.\n'
            '2. Attach positive lead of voltmeter to pigtail.\n'
            '3. Attach common lead of voltmeter to ground.\n'
            '4. Press one of the voltage test buttons, wait for the\n'
            '     voltage to ramp up and stabilize, then record the\n'
            '     measured value in the adjacent entry box.\n'
            '5. Repeat this for each of the six voltage settings.\n'
            '6. When complete, press the "Disable HV" button.\n'
            '7. Click the "Next" button to continue.\n'
        )

        title_label = QLabel('Beam Test')
        title_label.setStyleSheet('font-size: 36pt;')
        instructions_txt = QLabel(instructions)

        # Create the three postive and three negative HV test buttons
        test_pos_100V_btn = QPushButton('Test 100 V')
        test_pos_100V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, pos_100V)
        )
        test_pos_500V_btn = QPushButton('Test 500 V')
        test_pos_500V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, pos_500V)
        )
        test_pos_1kV_btn = QPushButton('Test 1000 V')
        test_pos_1kV_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, pos_1kV)
        )
        test_neg_100V_btn = QPushButton('Test -100 V')
        test_neg_100V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, neg_100V)
        )
        test_neg_500V_btn = QPushButton('Test -500 V')
        test_neg_500V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, neg_500V)
        )
        test_neg_1kV_btn = QPushButton('Test -1000 V')
        test_neg_1kV_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, neg_1kV)
        )

        # Create the entry boxes for recording the measured voltage values
        self.beam_pos_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.beam_pos_100V_measurement.setValidator(self.lv_validator)
        self.beam_pos_100V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.beam_pos_100V_measurement.text()
            )
        )
        self.beam_pos_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.beam_pos_500V_measurement.setValidator(self.lv_validator)
        self.beam_pos_500V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.beam_pos_500V_measurement.text()
            )
        )
        self.beam_pos_1kV_measurement = QLineEdit(placeholderText='Enter measurement')
        self.beam_pos_1kV_measurement.setValidator(self.hv_validator)
        self.beam_pos_1kV_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.beam_pos_1kV_measurement.text()
            )
        )
        self.beam_neg_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.beam_neg_100V_measurement.setValidator(self.lv_validator)
        self.beam_neg_100V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.beam_neg_100V_measurement.text()
            )
        )
        self.beam_neg_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.beam_neg_500V_measurement.setValidator(self.lv_validator)
        self.beam_neg_500V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.beam_neg_500V_measurement.text()
            )
        )
        self.beam_neg_1kV_measurement = QLineEdit(placeholderText='Enter measurement')
        self.beam_neg_1kV_measurement.setValidator(self.hv_validator)
        self.beam_neg_1kV_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.beam_neg_1kV_measurement.text()
            )
        )

        disable_hv_btn = QPushButton('Disable HV')
        disable_hv_btn.clicked.connect(self.handle_disable_hv_btn)
        next_btn = QPushButton('Next')
        next_btn.clicked.connect(self.handle_next_btn)

        # Create vertical line
        vertical_line = QFrame(frameShape=QFrame.Shape.VLine)

        # Create the widget to hold the photo
        photo = QLabel()
        photo_path: Path = self.root_dir / 'assets' / 'beam.jpg'
        pixmap = QPixmap(photo_path)
        photo.setPixmap(pixmap)

        self.main_layout.addWidget(
            title_label, 0, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 2)
        self.main_layout.addWidget(test_pos_100V_btn, 2, 0)
        self.main_layout.addWidget(test_pos_500V_btn, 3, 0)
        self.main_layout.addWidget(test_pos_1kV_btn, 4, 0)
        self.main_layout.addWidget(test_neg_100V_btn, 5, 0)
        self.main_layout.addWidget(test_neg_500V_btn, 6, 0)
        self.main_layout.addWidget(test_neg_1kV_btn, 7, 0)
        self.main_layout.addWidget(self.beam_pos_100V_measurement, 2, 1)
        self.main_layout.addWidget(self.beam_pos_500V_measurement, 3, 1)
        self.main_layout.addWidget(self.beam_pos_1kV_measurement, 4, 1)
        self.main_layout.addWidget(self.beam_neg_100V_measurement, 5, 1)
        self.main_layout.addWidget(self.beam_neg_500V_measurement, 6, 1)
        self.main_layout.addWidget(self.beam_neg_1kV_measurement, 7, 1)
        self.main_layout.addWidget(disable_hv_btn, 8, 0, 1, 2)
        self.main_layout.addWidget(next_btn, 9, 0, 1, 2)
        self.main_layout.addWidget(vertical_line, 0, 2, 9, 1)
        self.main_layout.addWidget(photo, 0, 3, 9, 1)

        self.setLayout(self.main_layout)

    def create_ext_test_gui(self) -> None:
        window_width = 1150
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Extractor Channel Test')
        self.channel = 'EX'
        pos_100V = self.test_voltages[0]
        pos_500V = self.test_voltages[1]
        pos_1kV = self.test_voltages[2]
        neg_100V = f'-{self.test_voltages[0]}'
        neg_500V = f'-{self.test_voltages[1]}'
        neg_1kV = f'-{self.test_voltages[2]}'

        instructions: str = (
            '1. Plug HV pigtail into Extractor HV recepticle.\n'
            '2. Attach positive lead of voltmeter to pigtail.\n'
            '3. Attach common lead of voltmeter to ground.\n'
            '4. Press one of the voltage test buttons, wait for the\n'
            '     voltage to ramp up and stabilize, then record the\n'
            '     measured value in the adjacent entry box.\n'
            '5. Repeat this for each of the six voltage settings.\n'
            '6. When complete, press the "Disable HV" button.\n'
            '7. Click the "Next" button to continue.\n'
        )

        title_label = QLabel('Ext. Test')
        title_label.setStyleSheet('font-size: 36pt;')
        instructions_txt = QLabel(instructions)

        # Create the three postive and three negative HV test buttons
        test_pos_100V_btn = QPushButton('Test 100 V')
        test_pos_100V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, pos_100V)
        )
        test_pos_500V_btn = QPushButton('Test 500 V')
        test_pos_500V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, pos_500V)
        )
        test_pos_1kV_btn = QPushButton('Test 1000 V')
        test_pos_1kV_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, pos_1kV)
        )
        test_neg_100V_btn = QPushButton('Test -100 V')
        test_neg_100V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, neg_100V)
        )
        test_neg_500V_btn = QPushButton('Test -500 V')
        test_neg_500V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, neg_500V)
        )
        test_neg_1kV_btn = QPushButton('Test -1000 V')
        test_neg_1kV_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, neg_1kV)
        )

        # Create the entry boxes for recording the measured voltage values
        self.ext_pos_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.ext_pos_100V_measurement.setValidator(self.lv_validator)
        self.ext_pos_100V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.ext_pos_100V_measurement.text()
            )
        )
        self.ext_pos_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.ext_pos_500V_measurement.setValidator(self.lv_validator)
        self.ext_pos_500V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.ext_pos_500V_measurement.text()
            )
        )
        self.ext_pos_1kV_measurement = QLineEdit(placeholderText='Enter measurement')
        self.ext_pos_1kV_measurement.setValidator(self.hv_validator)
        self.ext_pos_1kV_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.ext_pos_1kV_measurement.text()
            )
        )
        self.ext_neg_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.ext_neg_100V_measurement.setValidator(self.lv_validator)
        self.ext_neg_100V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.ext_neg_100V_measurement.text()
            )
        )
        self.ext_neg_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.ext_neg_500V_measurement.setValidator(self.lv_validator)
        self.ext_neg_500V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.ext_neg_500V_measurement.text()
            )
        )
        self.ext_neg_1kV_measurement = QLineEdit(placeholderText='Enter measurement')
        self.ext_neg_1kV_measurement.setValidator(self.hv_validator)
        self.ext_neg_1kV_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.ext_neg_1kV_measurement.text()
            )
        )

        disable_hv_btn = QPushButton('Disable HV')
        disable_hv_btn.clicked.connect(self.handle_disable_hv_btn)
        next_btn = QPushButton('Next')
        next_btn.clicked.connect(self.handle_next_btn)

        # Create vertical line
        vertical_line = QFrame(frameShape=QFrame.Shape.VLine)

        # Create the widget to hold the photo
        photo = QLabel()
        photo_path: Path = self.root_dir / 'assets' / 'L1.jpg'
        pixmap = QPixmap(photo_path)
        photo.setPixmap(pixmap)

        self.main_layout.addWidget(
            title_label, 0, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 2)
        self.main_layout.addWidget(test_pos_100V_btn, 2, 0)
        self.main_layout.addWidget(test_pos_500V_btn, 3, 0)
        self.main_layout.addWidget(test_pos_1kV_btn, 4, 0)
        self.main_layout.addWidget(test_neg_100V_btn, 5, 0)
        self.main_layout.addWidget(test_neg_500V_btn, 6, 0)
        self.main_layout.addWidget(test_neg_1kV_btn, 7, 0)
        self.main_layout.addWidget(self.ext_pos_100V_measurement, 2, 1)
        self.main_layout.addWidget(self.ext_pos_500V_measurement, 3, 1)
        self.main_layout.addWidget(self.ext_pos_1kV_measurement, 4, 1)
        self.main_layout.addWidget(self.ext_neg_100V_measurement, 5, 1)
        self.main_layout.addWidget(self.ext_neg_500V_measurement, 6, 1)
        self.main_layout.addWidget(self.ext_neg_1kV_measurement, 7, 1)
        self.main_layout.addWidget(disable_hv_btn, 8, 0, 1, 2)
        self.main_layout.addWidget(next_btn, 9, 0, 1, 2)
        self.main_layout.addWidget(vertical_line, 0, 2, 9, 1)
        self.main_layout.addWidget(photo, 0, 3, 9, 1)

        self.setLayout(self.main_layout)

    def create_L1_test_gui(self) -> None:
        window_width = 1150
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Lens 1 Channel Test')
        self.channel = 'L1'
        pos_100V = self.test_voltages[0]
        pos_500V = self.test_voltages[1]
        pos_1kV = self.test_voltages[2]
        neg_100V = f'-{self.test_voltages[0]}'
        neg_500V = f'-{self.test_voltages[1]}'
        neg_1kV = f'-{self.test_voltages[2]}'

        instructions: str = (
            '1. Plug HV pigtail into Lens 1 HV recepticle.\n'
            '2. Attach positive lead of voltmeter to pigtail.\n'
            '3. Attach common lead of voltmeter to ground.\n'
            '4. Press one of the voltage test buttons, wait for the\n'
            '     voltage to ramp up and stabilize, then record the\n'
            '     measured value in the adjacent entry box.\n'
            '5. Repeat this for each of the six voltage settings.\n'
            '6. When complete, press the "Disable HV" button.\n'
            '7. Click the "Next" button to continue.\n'
        )

        title_label = QLabel('Lens 1 Test')
        title_label.setStyleSheet('font-size: 36pt;')
        instructions_txt = QLabel(instructions)

        # Create the three postive and three negative HV test buttons
        test_pos_100V_btn = QPushButton('Test 100 V')
        test_pos_100V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, pos_100V)
        )
        test_pos_500V_btn = QPushButton('Test 500 V')
        test_pos_500V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, pos_500V)
        )
        test_pos_1kV_btn = QPushButton('Test 1000 V')
        test_pos_1kV_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, pos_1kV)
        )
        test_neg_100V_btn = QPushButton('Test -100 V')
        test_neg_100V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, neg_100V)
        )
        test_neg_500V_btn = QPushButton('Test -500 V')
        test_neg_500V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, neg_500V)
        )
        test_neg_1kV_btn = QPushButton('Test -1000 V')
        test_neg_1kV_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, neg_1kV)
        )

        # Create the entry boxes for recording the measured voltage values
        self.L1_pos_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L1_pos_100V_measurement.setValidator(self.lv_validator)
        self.L1_pos_100V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L1_pos_100V_measurement.text()
            )
        )
        self.L1_pos_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L1_pos_500V_measurement.setValidator(self.lv_validator)
        self.L1_pos_500V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L1_pos_500V_measurement.text()
            )
        )
        self.L1_pos_1kV_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L1_pos_1kV_measurement.setValidator(self.hv_validator)
        self.L1_pos_1kV_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L1_pos_1kV_measurement.text()
            )
        )
        self.L1_neg_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L1_neg_100V_measurement.setValidator(self.lv_validator)
        self.L1_neg_100V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L1_neg_100V_measurement.text()
            )
        )
        self.L1_neg_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L1_neg_500V_measurement.setValidator(self.lv_validator)
        self.L1_neg_500V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L1_neg_500V_measurement.text()
            )
        )
        self.L1_neg_1kV_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L1_neg_1kV_measurement.setValidator(self.hv_validator)
        self.L1_neg_1kV_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L1_neg_1kV_measurement.text()
            )
        )

        disable_hv_btn = QPushButton('Disable HV')
        disable_hv_btn.clicked.connect(self.handle_disable_hv_btn)
        next_btn = QPushButton('Next')
        next_btn.clicked.connect(self.handle_next_btn)

        # Create vertical line
        vertical_line = QFrame(frameShape=QFrame.Shape.VLine)

        # Create the widget to hold the photo
        photo = QLabel()
        photo_path: Path = self.root_dir / 'assets' / 'L1.jpg'
        pixmap = QPixmap(photo_path)
        photo.setPixmap(pixmap)

        self.main_layout.addWidget(
            title_label, 0, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 2)
        self.main_layout.addWidget(test_pos_100V_btn, 2, 0)
        self.main_layout.addWidget(test_pos_500V_btn, 3, 0)
        self.main_layout.addWidget(test_pos_1kV_btn, 4, 0)
        self.main_layout.addWidget(test_neg_100V_btn, 5, 0)
        self.main_layout.addWidget(test_neg_500V_btn, 6, 0)
        self.main_layout.addWidget(test_neg_1kV_btn, 7, 0)
        self.main_layout.addWidget(self.L1_pos_100V_measurement, 2, 1)
        self.main_layout.addWidget(self.L1_pos_500V_measurement, 3, 1)
        self.main_layout.addWidget(self.L1_pos_1kV_measurement, 4, 1)
        self.main_layout.addWidget(self.L1_neg_100V_measurement, 5, 1)
        self.main_layout.addWidget(self.L1_neg_500V_measurement, 6, 1)
        self.main_layout.addWidget(self.L1_neg_1kV_measurement, 7, 1)
        self.main_layout.addWidget(disable_hv_btn, 8, 0, 1, 2)
        self.main_layout.addWidget(next_btn, 9, 0, 1, 2)
        self.main_layout.addWidget(vertical_line, 0, 2, 9, 1)
        self.main_layout.addWidget(photo, 0, 3, 9, 1)

        self.setLayout(self.main_layout)

    def create_L2_test_gui(self) -> None:
        window_width = 1150
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Lens 2 Channel Test')
        self.channel = 'L2'
        pos_100V = self.test_voltages[0]
        pos_500V = self.test_voltages[1]
        pos_1kV = self.test_voltages[2]
        neg_100V = f'-{self.test_voltages[0]}'
        neg_500V = f'-{self.test_voltages[1]}'
        neg_1kV = f'-{self.test_voltages[2]}'

        instructions: str = (
            '1. Plug HV pigtail into Lens 2 HV recepticle.\n'
            '2. Attach positive lead of voltmeter to pigtail.\n'
            '3. Attach common lead of voltmeter to ground.\n'
            '4. Press one of the voltage test buttons, wait for the\n'
            '     voltage to ramp up and stabilize, then record the\n'
            '     measured value in the adjacent entry box.\n'
            '5. Repeat this for each of the six voltage settings.\n'
            '6. When complete, press the "Disable HV" button.\n'
            '7. Click the "Next" button to continue.\n'
        )

        title_label = QLabel('Lens 2 Test')
        title_label.setStyleSheet('font-size: 36pt;')
        instructions_txt = QLabel(instructions)

        # Create the three postive and three negative HV test buttons
        test_pos_100V_btn = QPushButton('Test 100 V')
        test_pos_100V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, pos_100V)
        )
        test_pos_500V_btn = QPushButton('Test 500 V')
        test_pos_500V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, pos_500V)
        )
        test_pos_1kV_btn = QPushButton('Test 1000 V')
        test_pos_1kV_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, pos_1kV)
        )
        test_neg_100V_btn = QPushButton('Test -100 V')
        test_neg_100V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, neg_100V)
        )
        test_neg_500V_btn = QPushButton('Test -500 V')
        test_neg_500V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, neg_500V)
        )
        test_neg_1kV_btn = QPushButton('Test -1000 V')
        test_neg_1kV_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, neg_1kV)
        )

        # Create the entry boxes for recording the measured voltage values
        self.L2_pos_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L2_pos_100V_measurement.setValidator(self.lv_validator)
        self.L2_pos_100V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L2_pos_100V_measurement.text()
            )
        )
        self.L2_pos_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L2_pos_500V_measurement.setValidator(self.lv_validator)
        self.L2_pos_500V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L2_pos_500V_measurement.text()
            )
        )
        self.L2_pos_1kV_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L2_pos_1kV_measurement.setValidator(self.hv_validator)
        self.L2_pos_1kV_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L2_pos_1kV_measurement.text()
            )
        )
        self.L2_neg_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L2_neg_100V_measurement.setValidator(self.lv_validator)
        self.L2_neg_100V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L2_neg_100V_measurement.text()
            )
        )
        self.L2_neg_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L2_neg_500V_measurement.setValidator(self.lv_validator)
        self.L2_neg_500V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L2_neg_500V_measurement.text()
            )
        )
        self.L2_neg_1kV_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L2_neg_1kV_measurement.setValidator(self.hv_validator)
        self.L2_neg_1kV_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L2_neg_1kV_measurement.text()
            )
        )

        disable_hv_btn = QPushButton('Disable HV')
        disable_hv_btn.clicked.connect(self.handle_disable_hv_btn)
        next_btn = QPushButton('Next')
        next_btn.clicked.connect(self.handle_next_btn)

        # Create vertical line
        vertical_line = QFrame(frameShape=QFrame.Shape.VLine)

        # Create the widget to hold the photo
        photo = QLabel()
        photo_path: Path = self.root_dir / 'assets' / 'L2.jpg'
        pixmap = QPixmap(photo_path)
        photo.setPixmap(pixmap)

        self.main_layout.addWidget(
            title_label, 0, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 2)
        self.main_layout.addWidget(test_pos_100V_btn, 2, 0)
        self.main_layout.addWidget(test_pos_500V_btn, 3, 0)
        self.main_layout.addWidget(test_pos_1kV_btn, 4, 0)
        self.main_layout.addWidget(test_neg_100V_btn, 5, 0)
        self.main_layout.addWidget(test_neg_500V_btn, 6, 0)
        self.main_layout.addWidget(test_neg_1kV_btn, 7, 0)
        self.main_layout.addWidget(self.L2_pos_100V_measurement, 2, 1)
        self.main_layout.addWidget(self.L2_pos_500V_measurement, 3, 1)
        self.main_layout.addWidget(self.L2_pos_1kV_measurement, 4, 1)
        self.main_layout.addWidget(self.L2_neg_100V_measurement, 5, 1)
        self.main_layout.addWidget(self.L2_neg_500V_measurement, 6, 1)
        self.main_layout.addWidget(self.L2_neg_1kV_measurement, 7, 1)
        self.main_layout.addWidget(disable_hv_btn, 8, 0, 1, 2)
        self.main_layout.addWidget(next_btn, 9, 0, 1, 2)
        self.main_layout.addWidget(vertical_line, 0, 2, 9, 1)
        self.main_layout.addWidget(photo, 0, 3, 9, 1)

        self.setLayout(self.main_layout)

    def create_L3_test_gui(self) -> None:
        window_width = 1150
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Lens 3 Channel Test')
        self.channel = 'L3'
        pos_100V = self.test_voltages[0]
        pos_500V = self.test_voltages[1]
        pos_1kV = self.test_voltages[2]
        neg_100V = f'-{self.test_voltages[0]}'
        neg_500V = f'-{self.test_voltages[1]}'
        neg_1kV = f'-{self.test_voltages[2]}'

        instructions: str = (
            '1. Plug HV pigtail into Beam HV recepticle.\n'
            '2. Attach positive lead of voltmeter to pigtail.\n'
            '3. Attach common lead of voltmeter to ground.\n'
            '4. Press one of the voltage test buttons, wait for the\n'
            '     voltage to ramp up and stabilize, then record the\n'
            '     measured value in the adjacent entry box.\n'
            '5. Repeat this for each of the six voltage settings.\n'
            '6. When complete, press the "Disable HV" button.\n'
            '7. Click the "Next" button to continue.\n'
        )

        title_label = QLabel('Lens 3 Test')
        title_label.setStyleSheet('font-size: 36pt;')
        instructions_txt = QLabel(instructions)

        # Create the three postive and three negative HV test buttons
        test_pos_100V_btn = QPushButton('Test 100 V')
        test_pos_100V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, pos_100V)
        )
        test_pos_500V_btn = QPushButton('Test 500 V')
        test_pos_500V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, pos_500V)
        )
        test_pos_1kV_btn = QPushButton('Test 1000 V')
        test_pos_1kV_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, pos_1kV)
        )
        test_neg_100V_btn = QPushButton('Test -100 V')
        test_neg_100V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, neg_100V)
        )
        test_neg_500V_btn = QPushButton('Test -500 V')
        test_neg_500V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, neg_500V)
        )
        test_neg_1kV_btn = QPushButton('Test -1000 V')
        test_neg_1kV_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, neg_1kV)
        )

        # Create the entry boxes for recording the measured voltage values
        self.L3_pos_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L3_pos_100V_measurement.setValidator(self.lv_validator)
        self.L3_pos_100V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L3_pos_100V_measurement.text()
            )
        )
        self.L3_pos_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L3_pos_500V_measurement.setValidator(self.lv_validator)
        self.L3_pos_100V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L3_pos_500V_measurement.text()
            )
        )
        self.L3_pos_1kV_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L3_pos_1kV_measurement.setValidator(self.hv_validator)
        self.L3_pos_100V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L3_pos_1kV_measurement.text()
            )
        )
        self.L3_neg_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L3_neg_100V_measurement.setValidator(self.lv_validator)
        self.L3_neg_100V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L3_neg_100V_measurement.text()
            )
        )
        self.L3_neg_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L3_neg_500V_measurement.setValidator(self.lv_validator)
        self.L3_neg_500V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L3_neg_500V_measurement.text()
            )
        )
        self.L3_neg_1kV_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L3_neg_1kV_measurement.setValidator(self.hv_validator)
        self.L3_neg_1kV_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L3_neg_1kV_measurement.text()
            )
        )

        disable_hv_btn = QPushButton('Disable HV')
        disable_hv_btn.clicked.connect(self.handle_disable_hv_btn)
        next_btn = QPushButton('Next')
        next_btn.clicked.connect(self.handle_next_btn)

        # Create vertical line
        vertical_line = QFrame(frameShape=QFrame.Shape.VLine)

        # Create the widget to hold the photo
        photo = QLabel()
        photo_path: Path = self.root_dir / 'assets' / 'L3.jpg'
        pixmap = QPixmap(photo_path)
        photo.setPixmap(pixmap)

        self.main_layout.addWidget(
            title_label, 0, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 2)
        self.main_layout.addWidget(test_pos_100V_btn, 2, 0)
        self.main_layout.addWidget(test_pos_500V_btn, 3, 0)
        self.main_layout.addWidget(test_pos_1kV_btn, 4, 0)
        self.main_layout.addWidget(test_neg_100V_btn, 5, 0)
        self.main_layout.addWidget(test_neg_500V_btn, 6, 0)
        self.main_layout.addWidget(test_neg_1kV_btn, 7, 0)
        self.main_layout.addWidget(self.L3_pos_100V_measurement, 2, 1)
        self.main_layout.addWidget(self.L3_pos_500V_measurement, 3, 1)
        self.main_layout.addWidget(self.L3_pos_1kV_measurement, 4, 1)
        self.main_layout.addWidget(self.L3_neg_100V_measurement, 5, 1)
        self.main_layout.addWidget(self.L3_neg_500V_measurement, 6, 1)
        self.main_layout.addWidget(self.L3_neg_1kV_measurement, 7, 1)
        self.main_layout.addWidget(disable_hv_btn, 8, 0, 1, 2)
        self.main_layout.addWidget(next_btn, 9, 0, 1, 2)
        self.main_layout.addWidget(vertical_line, 0, 2, 9, 1)
        self.main_layout.addWidget(photo, 0, 3, 9, 1)

        self.setLayout(self.main_layout)

    def create_L4_test_gui(self) -> None:
        window_width = 1150
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Lens 4 Channel Test')
        self.channel = 'L4'
        pos_100V = self.test_voltages[0]
        pos_500V = self.test_voltages[1]
        pos_1kV = self.test_voltages[2]
        neg_100V = f'-{self.test_voltages[0]}'
        neg_500V = f'-{self.test_voltages[1]}'
        neg_1kV = f'-{self.test_voltages[2]}'

        instructions: str = (
            '1. Plug HV pigtail into Lens 4 HV recepticle.\n'
            '2. Attach positive lead of voltmeter to pigtail.\n'
            '3. Attach common lead of voltmeter to ground.\n'
            '4. Press one of the voltage test buttons, wait for the\n'
            '     voltage to ramp up and stabilize, then record the\n'
            '     measured value in the adjacent entry box.\n'
            '5. Repeat this for each of the six voltage settings.\n'
            '6. When complete, press the "Disable HV" button.\n'
            '7. Click the "Next" button to continue.\n'
        )

        title_label = QLabel('Lens 4 Test')
        title_label.setStyleSheet('font-size: 36pt;')
        instructions_txt = QLabel(instructions)

        # Create the three postive and three negative HV test buttons
        test_pos_100V_btn = QPushButton('Test 100 V')
        test_pos_100V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, pos_100V)
        )
        test_pos_500V_btn = QPushButton('Test 500 V')
        test_pos_500V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, pos_500V)
        )
        test_pos_1kV_btn = QPushButton('Test 1000 V')
        test_pos_1kV_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, pos_1kV)
        )
        test_neg_100V_btn = QPushButton('Test -100 V')
        test_neg_100V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, neg_100V)
        )
        test_neg_500V_btn = QPushButton('Test -500 V')
        test_neg_500V_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, neg_500V)
        )
        test_neg_1kV_btn = QPushButton('Test -1000 V')
        test_neg_1kV_btn.clicked.connect(
            lambda: self.handle_test_hv_btn(self.channel, neg_1kV)
        )

        # Create the entry boxes for recording the measured voltage values
        self.L4_pos_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L4_pos_100V_measurement.setValidator(self.lv_validator)
        self.L4_pos_100V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L4_pos_100V_measurement.text()
            )
        )
        self.L4_pos_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L4_pos_500V_measurement.setValidator(self.lv_validator)
        self.L4_pos_500V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L4_pos_500V_measurement.text()
            )
        )
        self.L4_pos_1kV_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L4_pos_1kV_measurement.setValidator(self.hv_validator)
        self.L4_pos_1kV_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L4_pos_1kV_measurement.text()
            )
        )
        self.L4_neg_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L4_neg_100V_measurement.setValidator(self.lv_validator)
        self.L4_neg_100V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L4_neg_100V_measurement.text()
            )
        )
        self.L4_neg_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L4_neg_500V_measurement.setValidator(self.lv_validator)
        self.L4_neg_500V_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L4_neg_500V_measurement.text()
            )
        )
        self.L4_neg_1kV_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L4_neg_1kV_measurement.setValidator(self.hv_validator)
        self.L4_neg_1kV_measurement.returnPressed.connect(
            lambda: self.handle_voltage_returnPressed(
                self.channel, self.L4_neg_1kV_measurement.text()
            )
        )

        disable_hv_btn = QPushButton('Disable HV')
        disable_hv_btn.clicked.connect(self.handle_disable_hv_btn)
        next_btn = QPushButton('Next')
        next_btn.clicked.connect(self.handle_next_btn)

        # Create vertical line
        vertical_line = QFrame(frameShape=QFrame.Shape.VLine)

        # Create the widget to hold the photo
        photo = QLabel()
        photo_path: Path = self.root_dir / 'assets' / 'L4.jpg'
        pixmap = QPixmap(photo_path)
        photo.setPixmap(pixmap)

        self.main_layout.addWidget(
            title_label, 0, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 2)
        self.main_layout.addWidget(test_pos_100V_btn, 2, 0)
        self.main_layout.addWidget(test_pos_500V_btn, 3, 0)
        self.main_layout.addWidget(test_pos_1kV_btn, 4, 0)
        self.main_layout.addWidget(test_neg_100V_btn, 5, 0)
        self.main_layout.addWidget(test_neg_500V_btn, 6, 0)
        self.main_layout.addWidget(test_neg_1kV_btn, 7, 0)
        self.main_layout.addWidget(self.L4_pos_100V_measurement, 2, 1)
        self.main_layout.addWidget(self.L4_pos_500V_measurement, 3, 1)
        self.main_layout.addWidget(self.L4_pos_1kV_measurement, 4, 1)
        self.main_layout.addWidget(self.L4_neg_100V_measurement, 5, 1)
        self.main_layout.addWidget(self.L4_neg_500V_measurement, 6, 1)
        self.main_layout.addWidget(self.L4_neg_1kV_measurement, 7, 1)
        self.main_layout.addWidget(disable_hv_btn, 8, 0, 1, 2)
        self.main_layout.addWidget(next_btn, 9, 0, 1, 2)
        self.main_layout.addWidget(vertical_line, 0, 2, 9, 1)
        self.main_layout.addWidget(photo, 0, 3, 9, 1)

        self.setLayout(self.main_layout)

    def create_sol_test_gui(self) -> None:
        window_width = 1150
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Solenoid Channel Test')

        instructions: str = (
            '1. Plug in a 2-pin Fischer connector to the solenoid\n'
            '     current recepticle.\n'
            '2. Plug in the current tester connector to other end of\n'
            '     the 2-pin Fischer connector cable.\n'
            '3. Set up a multimeter to measure current. Set the scale\n'
            '     to so that the meter can read up to 2.5 A.\n'
            '4. Attach the positive lead to one pin of the current\n'
            '     connector.\n'
            '5. Attach the common lead to the other pin of the\n'
            '     current connector.\n'
            '6. Press one of the current test buttons, wait for the\n'
            '     current to ramp up and stabilize, then record the\n'
            '     measured value in the adjacent entry box.\n'
            '7. Repeat this for each of the three current settings.\n'
            '8. When complete, press the "Disable Solenoid" button.\n'
            '9. Click the "Next" button to continue.\n'
        )

        title_label = QLabel('Sol. Test')
        title_label.setStyleSheet('font-size: 36pt;')
        instructions_txt = QLabel(instructions)

        # Create the three current test buttons
        current1_btn = QPushButton('Test 0.3 A')
        current1_btn.clicked.connect(
            lambda: self.handle_test_sol_btn(self.test_currents[0])
        )
        current2_btn = QPushButton('Test 1.2 A')
        current2_btn.clicked.connect(
            lambda: self.handle_test_sol_btn(self.test_currents[1])
        )
        current3_btn = QPushButton('Test 2.5 A')
        current3_btn.clicked.connect(
            lambda: self.handle_test_sol_btn(self.test_currents[2])
        )

        # Create the entry boxes for recording the measured current values
        self.current1_measurement = QLineEdit(placeholderText='Enter measurement')
        self.current1_measurement.setValidator(self.sol_validator)
        self.current1_measurement.returnPressed.connect(
            lambda: self.handle_current_returnPressed(self.current1_measurement.text())
        )
        self.current2_measurement = QLineEdit(placeholderText='Enter measurement')
        self.current2_measurement.setValidator(self.sol_validator)
        self.current2_measurement.returnPressed.connect(
            lambda: self.handle_current_returnPressed(self.current2_measurement.text())
        )
        self.current3_measurement = QLineEdit(placeholderText='Enter measurement')
        self.current3_measurement.setValidator(self.sol_validator)
        self.current3_measurement.returnPressed.connect(
            lambda: self.handle_current_returnPressed(self.current3_measurement.text())
        )

        disable_sol_btn = QPushButton('Disable Solenoid')
        disable_sol_btn.clicked.connect(self.handle_disable_sol_btn)
        next_btn = QPushButton('Next')
        next_btn.clicked.connect(self.handle_next_btn)

        # Create a vertical line
        vertical_line = QFrame()
        vertical_line.setFrameShape(QFrame.Shape.VLine)

        # Create the widget to hold the photo
        photo = QLabel()
        photo_path: Path = self.root_dir / 'assets' / 'sol.jpg'
        pixmap = QPixmap(photo_path)
        photo.setPixmap(pixmap)

        self.main_layout.addWidget(
            title_label, 0, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 2)
        self.main_layout.addWidget(current1_btn, 2, 0)
        self.main_layout.addWidget(current2_btn, 3, 0)
        self.main_layout.addWidget(current3_btn, 4, 0)
        self.main_layout.addWidget(self.current1_measurement, 2, 1)
        self.main_layout.addWidget(self.current2_measurement, 3, 1)
        self.main_layout.addWidget(self.current3_measurement, 4, 1)
        self.main_layout.addWidget(disable_sol_btn, 5, 0, 1, 2)
        self.main_layout.addWidget(next_btn, 6, 0, 1, 2)

        self.main_layout.addWidget(vertical_line, 0, 2, 7, 1)

        self.main_layout.addWidget(photo, 0, 3, 7, 1)
        self.setLayout(self.main_layout)

    def handle_disable_hv_btn(self) -> None:
        if self.get_hv_enable_state() is True:
            self.hvps.disable_high_voltage()
        self.hvps.set_voltage(self.channel, '0')

    def handle_test_hv_btn(self, channel: str, voltage: str) -> None:
        if self.get_hv_enable_state() is False:
            self.hvps.enable_high_voltage()
        self.hvps.set_voltage(channel, voltage)

    def handle_test_sol_btn(self, current: str) -> None:
        if self.get_sol_enable_state() is False:
            self.hvps.enable_solenoid_current()
        self.hvps.set_solenoid_current(current)

    def handle_voltage_returnPressed(self, channel: str, measurement: str) -> None:
        readback = self.hvps.get_voltage(channel)
        self.channel_readbacks.append(readback)
        self.channel_measurements.append(measurement)

    def handle_current_returnPressed(self, measurement: str) -> None:
        readback = self.hvps.get_current('SL')
        self.channel_readbacks.append(readback)
        self.channel_measurements.append(measurement)

    def handle_disable_sol_btn(self) -> None:
        if self.get_sol_enable_state() is True:
            self.hvps.disable_solenoid_current()

    def closeEvent(self, event) -> None:
        if self.get_hv_enable_state is True:
            self.hvps.disable_high_voltage()
            self.hvps.set_voltage(self.channel, '0')
        if self.get_sol_enable_state is True:
            self.hvps.disable_solenoid_current()
            self.hvps.set_solenoid_current('0')
        self.window_closed.emit()
        super().closeEvent(event)
