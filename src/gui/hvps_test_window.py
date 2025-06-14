from pathlib import Path
from typing import Callable

from PySide6.QtCore import QRegularExpression, Qt, Signal
from PySide6.QtGui import (
    QCloseEvent,
    QIcon,
    QPixmap,
    QRegularExpressionValidator,
)
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QWidget,
)
from qt_material import apply_stylesheet

from helpers.helpers import get_root_dir

from ..hvps.hvps_api import HVPSv3


class HVPSTestWindow(QMainWindow):
    test_complete = Signal(dict, dict)
    window_closed = Signal()

    def __init__(self, hvps: HVPSv3, occupied_channels: list[str], parent=None) -> None:
        super().__init__(parent)

        # Get the HVPS object and the occupied channels
        self.hvps = hvps
        self.occupied_channels = occupied_channels

        # Define the voltages and currents used for testing the HVPS
        self.test_voltages: tuple[str, ...] = ('100', '500', '1000')  # volts
        self.test_currents: tuple[str, ...] = ('0.3', '1.2', '2.5')  # amps

        # Make empty list to hold the gui creation function list.
        self.test_stages: list[Callable] = []

        # Make lists to hold measurement and readback data
        # Initialize the lists with the proper length
        self.channel_readbacks: list[str]
        self.channel_measurements: list[str]

        if self.occupied_channels == ['SL']:
            self.channel_readbacks = ['unmeasured'] * 3
            self.channel_measurements = ['unmeasured'] * 3
        else:
            self.channel_readbacks = ['unmeasured'] * 6
            self.channel_measurements = ['unmeasured'] * 6

        # Make pre-populated dictionaries to hold the readback and measurement data
        self.readbacks: dict[str, list[str]] = {
            'BM': ['N/A'] * 6,
            'EX': ['N/A'] * 6,
            'L1': ['N/A'] * 6,
            'L2': ['N/A'] * 6,
            'L3': ['N/A'] * 6,
            'L4': ['N/A'] * 6,
            'SL': ['N/A'] * 3,
        }
        self.measurements: dict[str, list[str]] = {
            'BM': ['N/A'] * 6,
            'EX': ['N/A'] * 6,
            'L1': ['N/A'] * 6,
            'L2': ['N/A'] * 6,
            'L3': ['N/A'] * 6,
            'L4': ['N/A'] * 6,
            'SL': ['N/A'] * 3,
        }

        # Set the window Icon and style the window
        self.root_dir: Path = get_root_dir()
        icon_path: str = str(self.root_dir / 'assets' / 'hvps_icon.ico')
        self.setWindowIcon(QIcon(icon_path))
        apply_stylesheet(self, theme='dark_lightgreen.xml', invert_secondary=True)
        self.setStyleSheet(
            self.styleSheet() + """QLineEdit, QTextEdit {color: lightgreen;}"""
        )

        # Create the regex expressions to validate the entries in the QLineEdits
        lv_regex = QRegularExpression(r'^-?\d{0,3}+\.\d{1,1}$')
        hv_regex = QRegularExpression(r'^-?\d{0,4}+\.\d{1,1}$')
        sol_regex = QRegularExpression(r'^\d{0,1}+\.\d{1,2}$')
        self.lv_validator = QRegularExpressionValidator(lv_regex)
        self.hv_validator = QRegularExpressionValidator(hv_regex)
        self.sol_validator = QRegularExpressionValidator(sol_regex)

        # Create the main layout
        self.main_layout = QGridLayout()

        # Call the first gui window where the user selects the occupied channels.
        self.test_plan()

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Handles what happens when the window closes.
        Checks if the HV is still enabled. If it is, disables HV and sets
        the target of the current channel to zero.
        Checks if the solenoid is still enabled. If it is, disables the
        solenoid current and sets the solenoid current target to zero.
        Emits the window_closed Signal.
        """
        if self.get_hv_enable_state() is True:
            print('Turning off HV.')
            self.hvps.disable_high_voltage()
            self.hvps.set_voltage(self.channel, '0')
        if self.get_sol_enable_state() is True:
            print('Turning off current.')
            self.hvps.disable_solenoid_current()
            self.hvps.set_solenoid_current('0')
        self.window_closed.emit()
        super().closeEvent(event)

    def get_hv_enable_state(self) -> bool:
        """
        Gets the state of the HV enable.
        Returns False if the HV enable is off.
        Returns True if the HV enable is on.

        Possible states:
            HV off / sol off = 'STATE0000'
            HV off / sol on = 'STATE0010'
            HV on / sol off = 'STATE0001'
            HV on / sol on = 'STATE0011'
        """
        state: str = self.hvps.get_state()
        if state == 'STATE0000' or state == 'STATE0010':
            return False
        return True

    def get_sol_enable_state(self) -> bool:
        """
        Gets the state of the solenoid enable.
        Returns False if the solenoid enable is off.
        Returns True if the solenoid enable is on.

        Possible states:
            HV off / sol off = 'STATE0000'
            HV off / sol on = 'STATE0010'
            HV on / sol off = 'STATE0001'
            HV on / sol on = 'STATE0011'
        """
        state: str = self.hvps.get_state()
        if state == 'STATE0000' or state == 'STATE0001':
            return False
        return True

    def clear_layout(self, layouts: list[QLayout]) -> None:
        """
        Removes all widgets from the provided layouts.

        Args:
            layouts (list[QLayout]): A list of layout objects to clear.
        """
        for layout in layouts:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()

    def test_plan(self) -> None:
        """
        Creates a list of gui creation methods to call depending on which
        channels are in self.occupied_channels.
        Initializes the current_stage_index to zero.
        Calls the load_current_stage method.
        """
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
        """
        If the current_stage_index is less than the length of the test_stages list,
        clears the layout then calls the gui creator method at the current_stage_index.
        If current_stage_index is greater than the length of the test_stages list,
        emits the test_complete signal and closes the window.
        """
        if self.current_stage_index < len(self.test_stages):
            if self.current_stage_index > 0:
                self.clear_layout([self.back_next_layout, self.main_layout])
            self.test_stages[self.current_stage_index]()
        else:
            self.test_complete.emit(self.readbacks, self.measurements)
            self.close()

    ##################################
    ##### CREATE THE GUI WINDOWS #####
    ##################################

    def create_beam_test_gui(self) -> None:
        """
        Creates the gui to test the beam channel
        """
        window_width = 1150
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Beam Channel Test')
        self.channel: str = 'BM'

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
        self.test_pos_100V_btn = QPushButton('Test 100 V')
        self.test_pos_500V_btn = QPushButton('Test 500 V')
        self.test_pos_1kV_btn = QPushButton('Test 1000 V')
        self.test_neg_100V_btn = QPushButton('Test -100 V')
        self.test_neg_500V_btn = QPushButton('Test -500 V')
        self.test_neg_1kV_btn = QPushButton('Test -1000 V')
        self.hv_buttons = [
            self.test_pos_100V_btn,
            self.test_pos_500V_btn,
            self.test_pos_1kV_btn,
            self.test_neg_100V_btn,
            self.test_neg_500V_btn,
            self.test_neg_1kV_btn,
        ]

        # When the button has focus and return/enter is pressed, the button is clicked.
        for button in self.hv_buttons:
            button.setAutoDefault(True)

        # Connect the button clicked Signal to the handle_test_hv_btn Slot
        self.test_pos_100V_btn.clicked.connect(self.handle_test_pos_100V_btn)
        self.test_pos_500V_btn.clicked.connect(self.handle_test_pos_500V_btn)
        self.test_pos_1kV_btn.clicked.connect(self.handle_test_pos_1kV_btn)
        self.test_neg_100V_btn.clicked.connect(self.handle_test_neg_100V_btn)
        self.test_neg_500V_btn.clicked.connect(self.handle_test_neg_500V_btn)
        self.test_neg_1kV_btn.clicked.connect(self.handle_test_neg_1kV_btn)

        # Create the entry boxes for recording the measured voltage values
        self.beam_pos_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.beam_pos_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.beam_pos_1kV_measurement = QLineEdit(placeholderText='Enter measurement')
        self.beam_neg_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.beam_neg_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.beam_neg_1kV_measurement = QLineEdit(placeholderText='Enter measurement')

        # Set the QLine edits to be disabled
        self.beam_pos_100V_measurement.setEnabled(False)
        self.beam_pos_500V_measurement.setEnabled(False)
        self.beam_pos_1kV_measurement.setEnabled(False)
        self.beam_neg_100V_measurement.setEnabled(False)
        self.beam_neg_500V_measurement.setEnabled(False)
        self.beam_neg_1kV_measurement.setEnabled(False)

        # Set the validators
        # self.beam_pos_100V_measurement.setValidator(self.lv_validator)
        # self.beam_pos_500V_measurement.setValidator(self.lv_validator)
        # self.beam_pos_1kV_measurement.setValidator(self.hv_validator)
        # self.beam_neg_100V_measurement.setValidator(self.lv_validator)
        # self.beam_neg_500V_measurement.setValidator(self.lv_validator)
        # self.beam_neg_1kV_measurement.setValidator(self.hv_validator)

        # Connect the returnPressed Signals to the handle_voltage_returnPressed Slot
        self.beam_pos_100V_measurement.returnPressed.connect(
            self.handle_beam_pos_100V_entered
        )
        self.beam_pos_500V_measurement.returnPressed.connect(
            self.handle_beam_pos_500V_entered
        )
        self.beam_pos_1kV_measurement.returnPressed.connect(
            self.handle_beam_pos_1kV_entered
        )
        self.beam_neg_100V_measurement.returnPressed.connect(
            self.handle_beam_neg_100V_entered
        )
        self.beam_neg_500V_measurement.returnPressed.connect(
            self.handle_beam_neg_500V_entered
        )
        self.beam_neg_1kV_measurement.returnPressed.connect(
            self.handle_beam_neg_1kV_entered
        )

        # Create the `Disable HV` and `Next` buttons
        disable_hv_btn = QPushButton('Disable HV')
        self.back_btn = QPushButton('Back')
        self.next_btn = QPushButton('Next')

        # When the button has focus and return/enter is pressed, the button is clicked.
        disable_hv_btn.setAutoDefault(True)
        self.next_btn.setAutoDefault(True)
        self.back_btn.setAutoDefault(True)

        # Connect the button clicked Signal to the handle Slots
        disable_hv_btn.clicked.connect(self.handle_disable_hv_btn)
        self.back_btn.clicked.connect(self.handle_back_btn)
        self.next_btn.clicked.connect(self.handle_next_btn)

        # Create vertical line
        vertical_line = QFrame(frameShape=QFrame.Shape.VLine)

        # Create the widget to hold the photo
        photo = QLabel()
        photo_path: Path = self.root_dir / 'assets' / 'beam.jpg'
        pixmap = QPixmap(photo_path)
        photo.setPixmap(pixmap)

        self.back_next_layout = QGridLayout()
        self.back_next_layout.addWidget(self.back_btn, 0, 0)
        self.back_next_layout.addWidget(self.next_btn, 0, 1)

        self.main_layout.addWidget(
            title_label, 0, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 2)
        self.main_layout.addWidget(self.test_pos_100V_btn, 2, 0)
        self.main_layout.addWidget(self.test_pos_500V_btn, 3, 0)
        self.main_layout.addWidget(self.test_pos_1kV_btn, 4, 0)
        self.main_layout.addWidget(self.test_neg_100V_btn, 5, 0)
        self.main_layout.addWidget(self.test_neg_500V_btn, 6, 0)
        self.main_layout.addWidget(self.test_neg_1kV_btn, 7, 0)
        self.main_layout.addWidget(self.beam_pos_100V_measurement, 2, 1)
        self.main_layout.addWidget(self.beam_pos_500V_measurement, 3, 1)
        self.main_layout.addWidget(self.beam_pos_1kV_measurement, 4, 1)
        self.main_layout.addWidget(self.beam_neg_100V_measurement, 5, 1)
        self.main_layout.addWidget(self.beam_neg_500V_measurement, 6, 1)
        self.main_layout.addWidget(self.beam_neg_1kV_measurement, 7, 1)
        self.main_layout.addWidget(disable_hv_btn, 8, 0, 1, 2)
        self.main_layout.addLayout(self.back_next_layout, 9, 0, 1, 2)
        self.main_layout.addWidget(vertical_line, 0, 2, 9, 1)
        self.main_layout.addWidget(photo, 0, 3, 9, 1)

        container = QWidget()
        container.setLayout(self.main_layout)

        self.setCentralWidget(container)

        # Set the focus on the first button
        self.test_pos_100V_btn.setFocus()

    def create_ext_test_gui(self) -> None:
        """
        Creates the gui to test the Extractor channel.
        """
        window_width = 1150
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Extractor Channel Test')
        self.channel = 'EX'

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
        self.test_pos_100V_btn = QPushButton('Test 100 V')
        self.test_pos_500V_btn = QPushButton('Test 500 V')
        self.test_pos_1kV_btn = QPushButton('Test 1000 V')
        self.test_neg_100V_btn = QPushButton('Test -100 V')
        self.test_neg_500V_btn = QPushButton('Test -500 V')
        self.test_neg_1kV_btn = QPushButton('Test -1000 V')
        self.hv_buttons = [
            self.test_pos_100V_btn,
            self.test_pos_500V_btn,
            self.test_pos_1kV_btn,
            self.test_neg_100V_btn,
            self.test_neg_500V_btn,
            self.test_neg_1kV_btn,
        ]

        # When the button has focus and return/enter is pressed, the button is clicked.
        for button in self.hv_buttons:
            button.setAutoDefault(True)

        # Connect the button clicked Signal to the handle_test_hv_btn Slot
        self.test_pos_100V_btn.clicked.connect(self.handle_test_pos_100V_btn)
        self.test_pos_500V_btn.clicked.connect(self.handle_test_pos_500V_btn)
        self.test_pos_1kV_btn.clicked.connect(self.handle_test_pos_1kV_btn)
        self.test_neg_100V_btn.clicked.connect(self.handle_test_neg_100V_btn)
        self.test_neg_500V_btn.clicked.connect(self.handle_test_neg_500V_btn)
        self.test_neg_1kV_btn.clicked.connect(self.handle_test_neg_1kV_btn)

        # Create the entry boxes for recording the measured voltage values
        self.ext_pos_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.ext_pos_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.ext_pos_1kV_measurement = QLineEdit(placeholderText='Enter measurement')
        self.ext_neg_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.ext_neg_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.ext_neg_1kV_measurement = QLineEdit(placeholderText='Enter measurement')

        # Set the QLine edits to be disabled
        self.ext_pos_100V_measurement.setEnabled(False)
        self.ext_pos_500V_measurement.setEnabled(False)
        self.ext_pos_1kV_measurement.setEnabled(False)
        self.ext_neg_100V_measurement.setEnabled(False)
        self.ext_neg_500V_measurement.setEnabled(False)
        self.ext_neg_1kV_measurement.setEnabled(False)

        # Create the validators
        # self.ext_pos_100V_measurement.setValidator(self.lv_validator)
        # self.ext_pos_500V_measurement.setValidator(self.lv_validator)
        # self.ext_pos_1kV_measurement.setValidator(self.hv_validator)
        # self.ext_neg_100V_measurement.setValidator(self.lv_validator)
        # self.ext_neg_500V_measurement.setValidator(self.lv_validator)
        # self.ext_neg_1kV_measurement.setValidator(self.hv_validator)

        # Connect the returnPressed Signals to the handle_voltage_returnPressed Slot
        self.ext_pos_100V_measurement.returnPressed.connect(
            self.handle_ext_pos_100V_entered
        )
        self.ext_pos_500V_measurement.returnPressed.connect(
            self.handle_ext_pos_500V_entered
        )
        self.ext_pos_1kV_measurement.returnPressed.connect(
            self.handle_ext_pos_1kV_entered
        )
        self.ext_neg_100V_measurement.returnPressed.connect(
            self.handle_ext_neg_100V_entered
        )
        self.ext_neg_500V_measurement.returnPressed.connect(
            self.handle_ext_neg_500V_entered
        )
        self.ext_neg_1kV_measurement.returnPressed.connect(
            self.handle_ext_neg_1kV_entered
        )

        # Create the `Disable HV` and `Next` buttons
        disable_hv_btn = QPushButton('Disable HV')
        self.back_btn = QPushButton('Back')
        self.next_btn = QPushButton('Next')

        # When the button has focus and return/enter is pressed, the button is clicked.
        disable_hv_btn.setAutoDefault(True)
        self.next_btn.setAutoDefault(True)

        # Connect the button clicked Signal to the handle Slots
        disable_hv_btn.clicked.connect(self.handle_disable_hv_btn)
        self.back_btn.clicked.connect(self.handle_back_btn)
        self.next_btn.clicked.connect(self.handle_next_btn)

        # Create vertical line
        vertical_line = QFrame(frameShape=QFrame.Shape.VLine)

        # Create the widget to hold the photo
        photo = QLabel()
        photo_path: Path = self.root_dir / 'assets' / 'L1.jpg'
        pixmap = QPixmap(photo_path)
        photo.setPixmap(pixmap)

        self.back_next_layout = QGridLayout()
        self.back_next_layout.addWidget(self.back_btn, 0, 0)
        self.back_next_layout.addWidget(self.next_btn, 0, 1)

        self.main_layout.addWidget(
            title_label, 0, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 2)
        self.main_layout.addWidget(self.test_pos_100V_btn, 2, 0)
        self.main_layout.addWidget(self.test_pos_500V_btn, 3, 0)
        self.main_layout.addWidget(self.test_pos_1kV_btn, 4, 0)
        self.main_layout.addWidget(self.test_neg_100V_btn, 5, 0)
        self.main_layout.addWidget(self.test_neg_500V_btn, 6, 0)
        self.main_layout.addWidget(self.test_neg_1kV_btn, 7, 0)
        self.main_layout.addWidget(self.ext_pos_100V_measurement, 2, 1)
        self.main_layout.addWidget(self.ext_pos_500V_measurement, 3, 1)
        self.main_layout.addWidget(self.ext_pos_1kV_measurement, 4, 1)
        self.main_layout.addWidget(self.ext_neg_100V_measurement, 5, 1)
        self.main_layout.addWidget(self.ext_neg_500V_measurement, 6, 1)
        self.main_layout.addWidget(self.ext_neg_1kV_measurement, 7, 1)
        self.main_layout.addWidget(disable_hv_btn, 8, 0, 1, 2)
        self.main_layout.addLayout(self.back_next_layout, 9, 0, 1, 2)
        self.main_layout.addWidget(vertical_line, 0, 2, 9, 1)
        self.main_layout.addWidget(photo, 0, 3, 9, 1)

        container = QWidget()
        container.setLayout(self.main_layout)

        self.setCentralWidget(container)

        # Set the focus on the first button
        self.test_pos_100V_btn.setFocus()

    def create_L1_test_gui(self) -> None:
        """
        Creates the gui to test the Lens 1 channel
        """
        window_width = 1150
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Lens 1 Channel Test')
        self.channel = 'L1'

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
        self.test_pos_100V_btn = QPushButton('Test 100 V')
        self.test_pos_500V_btn = QPushButton('Test 500 V')
        self.test_pos_1kV_btn = QPushButton('Test 1000 V')
        self.test_neg_100V_btn = QPushButton('Test -100 V')
        self.test_neg_500V_btn = QPushButton('Test -500 V')
        self.test_neg_1kV_btn = QPushButton('Test -1000 V')
        self.hv_buttons = [
            self.test_pos_100V_btn,
            self.test_pos_500V_btn,
            self.test_pos_1kV_btn,
            self.test_neg_100V_btn,
            self.test_neg_500V_btn,
            self.test_neg_1kV_btn,
        ]

        # When the button has focus and return/enter is pressed, the button is clicked.
        for button in self.hv_buttons:
            button.setAutoDefault(True)

        # Connect the button clicked Signal to the handle_test_hv_btn Slot
        self.test_pos_100V_btn.clicked.connect(self.handle_test_pos_100V_btn)
        self.test_pos_500V_btn.clicked.connect(self.handle_test_pos_500V_btn)
        self.test_pos_1kV_btn.clicked.connect(self.handle_test_pos_1kV_btn)
        self.test_neg_100V_btn.clicked.connect(self.handle_test_neg_100V_btn)
        self.test_neg_500V_btn.clicked.connect(self.handle_test_neg_500V_btn)
        self.test_neg_1kV_btn.clicked.connect(self.handle_test_neg_1kV_btn)

        # Create the entry boxes for recording the measured voltage values
        self.L1_pos_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L1_pos_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L1_pos_1kV_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L1_neg_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L1_neg_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L1_neg_1kV_measurement = QLineEdit(placeholderText='Enter measurement')

        # Set the QLine edits to be disabled
        self.L1_pos_100V_measurement.setEnabled(False)
        self.L1_pos_500V_measurement.setEnabled(False)
        self.L1_pos_1kV_measurement.setEnabled(False)
        self.L1_neg_100V_measurement.setEnabled(False)
        self.L1_neg_500V_measurement.setEnabled(False)
        self.L1_neg_1kV_measurement.setEnabled(False)

        # Create the validators
        # self.L1_pos_100V_measurement.setValidator(self.lv_validator)
        # self.L1_pos_500V_measurement.setValidator(self.lv_validator)
        # self.L1_pos_1kV_measurement.setValidator(self.hv_validator)
        # self.L1_neg_100V_measurement.setValidator(self.lv_validator)
        # self.L1_neg_500V_measurement.setValidator(self.lv_validator)
        # self.L1_neg_1kV_measurement.setValidator(self.hv_validator)

        # Connect the returnPressed Signals to the handle_voltage_returnPressed Slot
        self.L1_pos_100V_measurement.returnPressed.connect(
            self.handle_L1_pos_100V_entered
        )
        self.L1_pos_500V_measurement.returnPressed.connect(
            self.handle_L1_pos_500V_entered
        )
        self.L1_pos_1kV_measurement.returnPressed.connect(
            self.handle_L1_pos_1kV_entered
        )
        self.L1_neg_100V_measurement.returnPressed.connect(
            self.handle_L1_neg_100V_entered
        )
        self.L1_neg_500V_measurement.returnPressed.connect(
            self.handle_L1_neg_500V_entered
        )
        self.L1_neg_1kV_measurement.returnPressed.connect(
            self.handle_L1_neg_1kV_entered
        )

        # Create the `Disable HV` and `Next` buttons
        disable_hv_btn = QPushButton('Disable HV')
        self.back_btn = QPushButton('Back')
        self.next_btn = QPushButton('Next')

        # When the button has focus and return/enter is pressed, the button is clicked.
        disable_hv_btn.setAutoDefault(True)
        self.next_btn.setAutoDefault(True)

        # Connect the button clicked Signal to the handle Slots
        disable_hv_btn.clicked.connect(self.handle_disable_hv_btn)
        self.back_btn.clicked.connect(self.handle_back_btn)
        self.next_btn.clicked.connect(self.handle_next_btn)

        # Create vertical line
        vertical_line = QFrame(frameShape=QFrame.Shape.VLine)

        # Create the widget to hold the photo
        photo = QLabel()
        photo_path: Path = self.root_dir / 'assets' / 'L1.jpg'
        pixmap = QPixmap(photo_path)
        photo.setPixmap(pixmap)

        self.back_next_layout = QGridLayout()
        self.back_next_layout.addWidget(self.back_btn, 0, 0)
        self.back_next_layout.addWidget(self.next_btn, 0, 1)

        self.main_layout.addWidget(
            title_label, 0, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 2)
        self.main_layout.addWidget(self.test_pos_100V_btn, 2, 0)
        self.main_layout.addWidget(self.test_pos_500V_btn, 3, 0)
        self.main_layout.addWidget(self.test_pos_1kV_btn, 4, 0)
        self.main_layout.addWidget(self.test_neg_100V_btn, 5, 0)
        self.main_layout.addWidget(self.test_neg_500V_btn, 6, 0)
        self.main_layout.addWidget(self.test_neg_1kV_btn, 7, 0)
        self.main_layout.addWidget(self.L1_pos_100V_measurement, 2, 1)
        self.main_layout.addWidget(self.L1_pos_500V_measurement, 3, 1)
        self.main_layout.addWidget(self.L1_pos_1kV_measurement, 4, 1)
        self.main_layout.addWidget(self.L1_neg_100V_measurement, 5, 1)
        self.main_layout.addWidget(self.L1_neg_500V_measurement, 6, 1)
        self.main_layout.addWidget(self.L1_neg_1kV_measurement, 7, 1)
        self.main_layout.addWidget(disable_hv_btn, 8, 0, 1, 2)
        self.main_layout.addLayout(self.back_next_layout, 9, 0, 1, 2)
        self.main_layout.addWidget(vertical_line, 0, 2, 9, 1)
        self.main_layout.addWidget(photo, 0, 3, 9, 1)

        container = QWidget()
        container.setLayout(self.main_layout)

        self.setCentralWidget(container)

        # Set the focus on the first button
        self.test_pos_100V_btn.setFocus()

    def create_L2_test_gui(self) -> None:
        """
        Creates the gui to test the Lens 2 channel
        """
        window_width = 1150
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Lens 2 Channel Test')
        self.channel = 'L2'

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
        self.test_pos_100V_btn = QPushButton('Test 100 V')
        self.test_pos_500V_btn = QPushButton('Test 500 V')
        self.test_pos_1kV_btn = QPushButton('Test 1000 V')
        self.test_neg_100V_btn = QPushButton('Test -100 V')
        self.test_neg_500V_btn = QPushButton('Test -500 V')
        self.test_neg_1kV_btn = QPushButton('Test -1000 V')
        self.hv_buttons = [
            self.test_pos_100V_btn,
            self.test_pos_500V_btn,
            self.test_pos_1kV_btn,
            self.test_neg_100V_btn,
            self.test_neg_500V_btn,
            self.test_neg_1kV_btn,
        ]

        # When the button has focus and return/enter is pressed, the button is clicked.
        for button in self.hv_buttons:
            button.setAutoDefault(True)

        # Connect the button clicked Signal to the handle_test_hv_btn Slot
        self.test_pos_100V_btn.clicked.connect(self.handle_test_pos_100V_btn)
        self.test_pos_500V_btn.clicked.connect(self.handle_test_pos_500V_btn)
        self.test_pos_1kV_btn.clicked.connect(self.handle_test_pos_1kV_btn)
        self.test_neg_100V_btn.clicked.connect(self.handle_test_neg_100V_btn)
        self.test_neg_500V_btn.clicked.connect(self.handle_test_neg_500V_btn)
        self.test_neg_1kV_btn.clicked.connect(self.handle_test_neg_1kV_btn)

        # Create the entry boxes for recording the measured voltage values
        self.L2_pos_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L2_pos_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L2_pos_1kV_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L2_neg_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L2_neg_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L2_neg_1kV_measurement = QLineEdit(placeholderText='Enter measurement')

        # Set the QLine edits to be disabled
        self.L2_pos_100V_measurement.setEnabled(False)
        self.L2_pos_500V_measurement.setEnabled(False)
        self.L2_pos_1kV_measurement.setEnabled(False)
        self.L2_neg_100V_measurement.setEnabled(False)
        self.L2_neg_500V_measurement.setEnabled(False)
        self.L2_neg_1kV_measurement.setEnabled(False)

        # Create the validator
        # self.L2_pos_100V_measurement.setValidator(self.lv_validator)
        # self.L2_pos_500V_measurement.setValidator(self.lv_validator)
        # self.L2_pos_1kV_measurement.setValidator(self.hv_validator)
        # self.L2_neg_100V_measurement.setValidator(self.lv_validator)
        # self.L2_neg_500V_measurement.setValidator(self.lv_validator)
        # self.L2_neg_1kV_measurement.setValidator(self.hv_validator)

        # Connect the returnPressed Signals to the handle_voltage_returnPressed Slot
        self.L2_pos_100V_measurement.returnPressed.connect(
            self.handle_L2_pos_100V_entered
        )
        self.L2_pos_500V_measurement.returnPressed.connect(
            self.handle_L2_pos_500V_entered
        )
        self.L2_pos_1kV_measurement.returnPressed.connect(
            self.handle_L2_pos_1kV_entered
        )
        self.L2_neg_100V_measurement.returnPressed.connect(
            self.handle_L2_neg_100V_entered
        )
        self.L2_neg_500V_measurement.returnPressed.connect(
            self.handle_L2_neg_500V_entered
        )
        self.L2_neg_1kV_measurement.returnPressed.connect(
            self.handle_L2_neg_1kV_entered
        )

        # Create the `Disable HV` and `Next` buttons
        disable_hv_btn = QPushButton('Disable HV')
        self.back_btn = QPushButton('Back')
        self.next_btn = QPushButton('Next')

        # When the button has focus and return/enter is pressed, the button is clicked.
        disable_hv_btn.setAutoDefault(True)
        self.next_btn.setAutoDefault(True)

        # Connect the button clicked Signal to the handle Slots
        disable_hv_btn.clicked.connect(self.handle_disable_hv_btn)
        self.back_btn.clicked.connect(self.handle_back_btn)
        self.next_btn.clicked.connect(self.handle_next_btn)

        # Create vertical line
        vertical_line = QFrame(frameShape=QFrame.Shape.VLine)

        # Create the widget to hold the photo
        photo = QLabel()
        photo_path: Path = self.root_dir / 'assets' / 'L2.jpg'
        pixmap = QPixmap(photo_path)
        photo.setPixmap(pixmap)

        self.back_next_layout = QGridLayout()
        self.back_next_layout.addWidget(self.back_btn, 0, 0)
        self.back_next_layout.addWidget(self.next_btn, 0, 1)

        self.main_layout.addWidget(
            title_label, 0, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 2)
        self.main_layout.addWidget(self.test_pos_100V_btn, 2, 0)
        self.main_layout.addWidget(self.test_pos_500V_btn, 3, 0)
        self.main_layout.addWidget(self.test_pos_1kV_btn, 4, 0)
        self.main_layout.addWidget(self.test_neg_100V_btn, 5, 0)
        self.main_layout.addWidget(self.test_neg_500V_btn, 6, 0)
        self.main_layout.addWidget(self.test_neg_1kV_btn, 7, 0)
        self.main_layout.addWidget(self.L2_pos_100V_measurement, 2, 1)
        self.main_layout.addWidget(self.L2_pos_500V_measurement, 3, 1)
        self.main_layout.addWidget(self.L2_pos_1kV_measurement, 4, 1)
        self.main_layout.addWidget(self.L2_neg_100V_measurement, 5, 1)
        self.main_layout.addWidget(self.L2_neg_500V_measurement, 6, 1)
        self.main_layout.addWidget(self.L2_neg_1kV_measurement, 7, 1)
        self.main_layout.addWidget(disable_hv_btn, 8, 0, 1, 2)
        self.main_layout.addLayout(self.back_next_layout, 9, 0, 1, 2)
        self.main_layout.addWidget(vertical_line, 0, 2, 9, 1)
        self.main_layout.addWidget(photo, 0, 3, 9, 1)

        container = QWidget()
        container.setLayout(self.main_layout)

        self.setCentralWidget(container)

        # Set the focus on the first button
        self.test_pos_100V_btn.setFocus()

    def create_L3_test_gui(self) -> None:
        """
        Creates the gui to test the Lens 3 channel
        """
        window_width = 1150
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Lens 3 Channel Test')
        self.channel = 'L3'

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
        self.test_pos_100V_btn = QPushButton('Test 100 V')
        self.test_pos_500V_btn = QPushButton('Test 500 V')
        self.test_pos_1kV_btn = QPushButton('Test 1000 V')
        self.test_neg_100V_btn = QPushButton('Test -100 V')
        self.test_neg_500V_btn = QPushButton('Test -500 V')
        self.test_neg_1kV_btn = QPushButton('Test -1000 V')
        self.hv_buttons = [
            self.test_pos_100V_btn,
            self.test_pos_500V_btn,
            self.test_pos_1kV_btn,
            self.test_neg_100V_btn,
            self.test_neg_500V_btn,
            self.test_neg_1kV_btn,
        ]

        # When the button has focus and return/enter is pressed, the button is clicked.
        for button in self.hv_buttons:
            button.setAutoDefault(True)

        # Connect the button clicked Signal to the handle_test_hv_btn Slot
        self.test_pos_100V_btn.clicked.connect(self.handle_test_pos_100V_btn)
        self.test_pos_500V_btn.clicked.connect(self.handle_test_pos_500V_btn)
        self.test_pos_1kV_btn.clicked.connect(self.handle_test_pos_1kV_btn)
        self.test_neg_100V_btn.clicked.connect(self.handle_test_neg_100V_btn)
        self.test_neg_500V_btn.clicked.connect(self.handle_test_neg_500V_btn)
        self.test_neg_1kV_btn.clicked.connect(self.handle_test_neg_1kV_btn)

        # Create the entry boxes for recording the measured voltage values
        self.L3_pos_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L3_pos_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L3_pos_1kV_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L3_neg_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L3_neg_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L3_neg_1kV_measurement = QLineEdit(placeholderText='Enter measurement')

        # Set the QLine edits to be disabled
        self.L3_pos_100V_measurement.setEnabled(False)
        self.L3_pos_500V_measurement.setEnabled(False)
        self.L3_pos_1kV_measurement.setEnabled(False)
        self.L3_neg_100V_measurement.setEnabled(False)
        self.L3_neg_500V_measurement.setEnabled(False)
        self.L3_neg_1kV_measurement.setEnabled(False)

        # Create the validators
        # self.L3_pos_100V_measurement.setValidator(self.lv_validator)
        # self.L3_pos_500V_measurement.setValidator(self.lv_validator)
        # self.L3_pos_1kV_measurement.setValidator(self.hv_validator)
        # self.L3_neg_100V_measurement.setValidator(self.lv_validator)
        # self.L3_neg_500V_measurement.setValidator(self.lv_validator)
        # self.L3_neg_1kV_measurement.setValidator(self.hv_validator)

        # Connect the returnPressed Signals to the handle_voltage_returnPressed Slot
        self.L3_pos_100V_measurement.returnPressed.connect(
            self.handle_L3_pos_100V_entered
        )
        self.L3_pos_500V_measurement.returnPressed.connect(
            self.handle_L3_pos_500V_entered
        )
        self.L3_pos_1kV_measurement.returnPressed.connect(
            self.handle_L3_pos_1kV_entered
        )
        self.L3_neg_100V_measurement.returnPressed.connect(
            self.handle_L3_neg_100V_entered
        )
        self.L3_neg_500V_measurement.returnPressed.connect(
            self.handle_L3_neg_500V_entered
        )
        self.L3_neg_1kV_measurement.returnPressed.connect(
            self.handle_L3_neg_1kV_entered
        )

        # Create the `Disable HV` and `Next` buttons
        disable_hv_btn = QPushButton('Disable HV')
        self.back_btn = QPushButton('Back')
        self.next_btn = QPushButton('Next')

        # When the button has focus and return/enter is pressed, the button is clicked.
        disable_hv_btn.setAutoDefault(True)
        self.next_btn.setAutoDefault(True)

        # Connect the button clicked Signal to the handle Slots
        disable_hv_btn.clicked.connect(self.handle_disable_hv_btn)
        self.back_btn.clicked.connect(self.handle_back_btn)
        self.next_btn.clicked.connect(self.handle_next_btn)

        # Create vertical line
        vertical_line = QFrame(frameShape=QFrame.Shape.VLine)

        # Create the widget to hold the photo
        photo = QLabel()
        photo_path: Path = self.root_dir / 'assets' / 'L3.jpg'
        pixmap = QPixmap(photo_path)
        photo.setPixmap(pixmap)

        self.back_next_layout = QGridLayout()
        self.back_next_layout.addWidget(self.back_btn, 0, 0)
        self.back_next_layout.addWidget(self.next_btn, 0, 1)

        self.main_layout.addWidget(
            title_label, 0, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 2)
        self.main_layout.addWidget(self.test_pos_100V_btn, 2, 0)
        self.main_layout.addWidget(self.test_pos_500V_btn, 3, 0)
        self.main_layout.addWidget(self.test_pos_1kV_btn, 4, 0)
        self.main_layout.addWidget(self.test_neg_100V_btn, 5, 0)
        self.main_layout.addWidget(self.test_neg_500V_btn, 6, 0)
        self.main_layout.addWidget(self.test_neg_1kV_btn, 7, 0)
        self.main_layout.addWidget(self.L3_pos_100V_measurement, 2, 1)
        self.main_layout.addWidget(self.L3_pos_500V_measurement, 3, 1)
        self.main_layout.addWidget(self.L3_pos_1kV_measurement, 4, 1)
        self.main_layout.addWidget(self.L3_neg_100V_measurement, 5, 1)
        self.main_layout.addWidget(self.L3_neg_500V_measurement, 6, 1)
        self.main_layout.addWidget(self.L3_neg_1kV_measurement, 7, 1)
        self.main_layout.addWidget(disable_hv_btn, 8, 0, 1, 2)
        self.main_layout.addLayout(self.back_next_layout, 9, 0, 1, 2)
        self.main_layout.addWidget(vertical_line, 0, 2, 9, 1)
        self.main_layout.addWidget(photo, 0, 3, 9, 1)

        container = QWidget()
        container.setLayout(self.main_layout)

        self.setCentralWidget(container)

        # Set the focus on the first button
        self.test_pos_100V_btn.setFocus()

    def create_L4_test_gui(self) -> None:
        """
        Creates the gui to test the Lens 4 channel
        """
        window_width = 1150
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Lens 4 Channel Test')
        self.channel = 'L4'

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
        self.test_pos_100V_btn = QPushButton('Test 100 V')
        self.test_pos_500V_btn = QPushButton('Test 500 V')
        self.test_pos_1kV_btn = QPushButton('Test 1000 V')
        self.test_neg_100V_btn = QPushButton('Test -100 V')
        self.test_neg_500V_btn = QPushButton('Test -500 V')
        self.test_neg_1kV_btn = QPushButton('Test -1000 V')
        self.hv_buttons = [
            self.test_pos_100V_btn,
            self.test_pos_500V_btn,
            self.test_pos_1kV_btn,
            self.test_neg_100V_btn,
            self.test_neg_500V_btn,
            self.test_neg_1kV_btn,
        ]

        # When the button has focus and return/enter is pressed, the button is clicked.
        for button in self.hv_buttons:
            button.setAutoDefault(True)

        # Connect the button clicked Signal to the handle_test_hv_btn Slot
        self.test_pos_100V_btn.clicked.connect(self.handle_test_pos_100V_btn)
        self.test_pos_500V_btn.clicked.connect(self.handle_test_pos_500V_btn)
        self.test_pos_1kV_btn.clicked.connect(self.handle_test_pos_1kV_btn)
        self.test_neg_100V_btn.clicked.connect(self.handle_test_neg_100V_btn)
        self.test_neg_500V_btn.clicked.connect(self.handle_test_neg_500V_btn)
        self.test_neg_1kV_btn.clicked.connect(self.handle_test_neg_1kV_btn)

        # Create the entry boxes for recording the measured voltage values
        self.L4_pos_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L4_pos_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L4_pos_1kV_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L4_neg_100V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L4_neg_500V_measurement = QLineEdit(placeholderText='Enter measurement')
        self.L4_neg_1kV_measurement = QLineEdit(placeholderText='Enter measurement')

        # Set the QLine edits to be disabled
        self.L4_pos_100V_measurement.setEnabled(False)
        self.L4_pos_500V_measurement.setEnabled(False)
        self.L4_pos_1kV_measurement.setEnabled(False)
        self.L4_neg_100V_measurement.setEnabled(False)
        self.L4_neg_500V_measurement.setEnabled(False)
        self.L4_neg_1kV_measurement.setEnabled(False)

        # Create the validators
        # self.L4_pos_100V_measurement.setValidator(self.lv_validator)
        # self.L4_pos_500V_measurement.setValidator(self.lv_validator)
        # self.L4_pos_1kV_measurement.setValidator(self.hv_validator)
        # self.L4_neg_100V_measurement.setValidator(self.lv_validator)
        # self.L4_neg_500V_measurement.setValidator(self.lv_validator)
        # self.L4_neg_1kV_measurement.setValidator(self.hv_validator)

        # Connect the returnPressed Signals to the handle_voltage_returnPressed Slot
        self.L4_pos_100V_measurement.returnPressed.connect(
            self.handle_L4_pos_100V_entered
        )
        self.L4_pos_500V_measurement.returnPressed.connect(
            self.handle_L4_pos_500V_entered
        )
        self.L4_pos_1kV_measurement.returnPressed.connect(
            self.handle_L4_pos_1kV_entered
        )
        self.L4_neg_100V_measurement.returnPressed.connect(
            self.handle_L4_neg_100V_entered
        )
        self.L4_neg_500V_measurement.returnPressed.connect(
            self.handle_L4_neg_500V_entered
        )
        self.L4_neg_1kV_measurement.returnPressed.connect(
            self.handle_L4_neg_1kV_entered
        )

        # Create the `Disable HV` and `Next` buttons
        disable_hv_btn = QPushButton('Disable HV')
        self.back_btn = QPushButton('Back')
        self.next_btn = QPushButton('Next')

        # When the next button has focus and return/enter is pressed, the button is clicked.
        disable_hv_btn.setAutoDefault(True)
        self.next_btn.setAutoDefault(True)

        # Connect the button clicked Signal to the handle Slots
        disable_hv_btn.clicked.connect(self.handle_disable_hv_btn)
        self.back_btn.clicked.connect(self.handle_back_btn)
        self.next_btn.clicked.connect(self.handle_next_btn)

        # Create vertical line
        vertical_line = QFrame(frameShape=QFrame.Shape.VLine)

        # Create the widget to hold the photo
        photo = QLabel()
        photo_path: Path = self.root_dir / 'assets' / 'L4.jpg'
        pixmap = QPixmap(photo_path)
        photo.setPixmap(pixmap)

        self.back_next_layout = QGridLayout()
        self.back_next_layout.addWidget(self.back_btn, 0, 0)
        self.back_next_layout.addWidget(self.next_btn, 0, 1)

        self.main_layout.addWidget(
            title_label, 0, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 2)
        self.main_layout.addWidget(self.test_pos_100V_btn, 2, 0)
        self.main_layout.addWidget(self.test_pos_500V_btn, 3, 0)
        self.main_layout.addWidget(self.test_pos_1kV_btn, 4, 0)
        self.main_layout.addWidget(self.test_neg_100V_btn, 5, 0)
        self.main_layout.addWidget(self.test_neg_500V_btn, 6, 0)
        self.main_layout.addWidget(self.test_neg_1kV_btn, 7, 0)
        self.main_layout.addWidget(self.L4_pos_100V_measurement, 2, 1)
        self.main_layout.addWidget(self.L4_pos_500V_measurement, 3, 1)
        self.main_layout.addWidget(self.L4_pos_1kV_measurement, 4, 1)
        self.main_layout.addWidget(self.L4_neg_100V_measurement, 5, 1)
        self.main_layout.addWidget(self.L4_neg_500V_measurement, 6, 1)
        self.main_layout.addWidget(self.L4_neg_1kV_measurement, 7, 1)
        self.main_layout.addWidget(disable_hv_btn, 8, 0, 1, 2)
        self.main_layout.addLayout(self.back_next_layout, 9, 0, 1, 2)
        self.main_layout.addWidget(vertical_line, 0, 2, 9, 1)
        self.main_layout.addWidget(photo, 0, 3, 9, 1)

        container = QWidget()
        container.setLayout(self.main_layout)

        self.setCentralWidget(container)

        # Set the focus on the first button
        self.test_pos_100V_btn.setFocus()

    def create_sol_test_gui(self) -> None:
        """
        Creates the gui to test the solenoid channel
        """
        window_width = 1150
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Solenoid Channel Test')
        self.channel = 'SL'

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
        self.current1_btn = QPushButton('Test 0.3 A')
        self.current2_btn = QPushButton('Test 1.2 A')
        self.current3_btn = QPushButton('Test 2.5 A')
        self.current_buttons: list[QPushButton] = [
            self.current1_btn,
            self.current2_btn,
            self.current3_btn,
        ]

        # When the button has focus and return/enter is pressed, the button is clicked.
        for button in self.current_buttons:
            button.setAutoDefault(True)

        self.current1_btn.clicked.connect(self.handle_test_sol_current1_btn)
        self.current2_btn.clicked.connect(self.handle_test_sol_current2_btn)
        self.current3_btn.clicked.connect(self.handle_test_sol_current3_btn)

        # Create the entry boxes for recording the measured current values
        self.current1_measurement = QLineEdit(placeholderText='Enter measurement')
        self.current2_measurement = QLineEdit(placeholderText='Enter measurement')
        self.current3_measurement = QLineEdit(placeholderText='Enter measurement')

        # Set the QLine edits to be disabled
        self.current1_measurement.setEnabled(False)
        self.current2_measurement.setEnabled(False)
        self.current3_measurement.setEnabled(False)

        # Create the validators
        # self.current1_measurement.setValidator(self.sol_validator)
        # self.current2_measurement.setValidator(self.sol_validator)
        # self.current3_measurement.setValidator(self.sol_validator)

        # Connect the button-clicked Signal to the handle-current-entered Slot
        self.current1_measurement.returnPressed.connect(self.handle_current1_entered)
        self.current2_measurement.returnPressed.connect(self.handle_current2_entered)
        self.current3_measurement.returnPressed.connect(self.handle_current3_entered)

        # Create the `Disable Solenoid` and `Next` buttons
        disable_sol_btn = QPushButton('Disable Solenoid')
        self.back_btn = QPushButton('Back')
        self.next_btn = QPushButton('Next')

        # When the button has focus and return/enter is pressed, the button is clicked.
        disable_sol_btn.setAutoDefault(True)
        self.next_btn.setAutoDefault(True)

        # Connect the button clicked Signal to the handle Slots
        disable_sol_btn.clicked.connect(self.handle_disable_sol_btn)
        self.back_btn.clicked.connect(self.handle_back_btn)
        self.next_btn.clicked.connect(self.handle_next_btn)

        # Create a vertical line
        vertical_line = QFrame()
        vertical_line.setFrameShape(QFrame.Shape.VLine)

        # Create the widget to hold the photo
        photo = QLabel()
        photo_path: Path = self.root_dir / 'assets' / 'sol.jpg'
        pixmap = QPixmap(photo_path)
        photo.setPixmap(pixmap)

        self.back_next_layout = QGridLayout()
        self.back_next_layout.addWidget(self.back_btn, 0, 0)
        self.back_next_layout.addWidget(self.next_btn, 0, 1)

        self.main_layout.addWidget(
            title_label, 0, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 2)
        self.main_layout.addWidget(self.current1_btn, 2, 0)
        self.main_layout.addWidget(self.current2_btn, 3, 0)
        self.main_layout.addWidget(self.current3_btn, 4, 0)
        self.main_layout.addWidget(self.current1_measurement, 2, 1)
        self.main_layout.addWidget(self.current2_measurement, 3, 1)
        self.main_layout.addWidget(self.current3_measurement, 4, 1)
        self.main_layout.addWidget(disable_sol_btn, 5, 0, 1, 2)
        self.main_layout.addLayout(self.back_next_layout, 6, 0, 1, 2)

        self.main_layout.addWidget(vertical_line, 0, 2, 7, 1)

        self.main_layout.addWidget(photo, 0, 3, 7, 1)

        container = QWidget()
        container.setLayout(self.main_layout)

        self.setCentralWidget(container)

        # Set the focus on the first button
        self.current1_btn.setFocus()

    ###############################
    ##### CREATE THE HANDLERS #####
    ###############################

    def handle_disable_hv_btn(self) -> None:
        """
        If the HV is enabled, disables the HV.
        Sets the current channel HV target to zero
        """
        if self.get_hv_enable_state() is True:
            self.hvps.disable_high_voltage()
        self.hvps.set_voltage(self.channel, '0')

    def handle_disable_sol_btn(self) -> None:
        """
        If the solenoid enable state is ON. Turns off the solenoid current.
        """
        if self.get_sol_enable_state() is True:
            self.hvps.disable_solenoid_current()

    def handle_back_btn(self) -> None:
        print('Back button pressed')

    def handle_next_btn(self) -> None:
        """
        If the HV is on, turn it off and set the current channel HV target to zero.
        If the solenoid is on, turn it off and set the solenoid current target to zero.
        Adds the channel measurements to the measurements dictionary
        Adds the channel readbacks to the readbacks dictionary
        Resets the channel_measurements and channel_readbacks lists
        Calls load_current_stage method.
        """

        if self.get_hv_enable_state() is True:  # disable btn not pressed
            self.hvps.disable_high_voltage()
            self.hvps.set_voltage(self.channel, '0')
        if self.get_sol_enable_state() is True:  # disable btn not pressed
            self.hvps.disable_solenoid_current()
            self.hvps.set_solenoid_current('0')

        self.measurements[self.channel] = self.channel_measurements
        self.readbacks[self.channel] = self.channel_readbacks

        if self.channel != 'SL':
            self.channel_measurements = ['unmeasured'] * 6
            self.channel_readbacks = ['unmeasured'] * 6
        else:
            self.channel_measurements = ['unmeasured'] * 3
            self.channel_readbacks = ['unmeasured'] * 3

        self.current_stage_index += 1
        self.load_current_stage()

    # Create the voltage test button handlers
    def handle_test_pos_100V_btn(self) -> None:
        """
        Tests the selected channel at 100 V
        """
        # Enable the QLineEdit
        match self.channel:
            case 'BM':
                self.beam_pos_100V_measurement.setEnabled(True)
                self.beam_pos_100V_measurement.setFocus()
            case 'EX':
                self.ext_pos_100V_measurement.setEnabled(True)
                self.ext_pos_100V_measurement.setFocus()
            case 'L1':
                self.L1_pos_100V_measurement.setEnabled(True)
                self.L1_pos_100V_measurement.setFocus()
            case 'L2':
                self.L2_pos_100V_measurement.setEnabled(True)
                self.L2_pos_100V_measurement.setFocus()
            case 'L3':
                self.L3_pos_100V_measurement.setEnabled(True)
                self.L3_pos_100V_measurement.setFocus()
            case 'L4':
                self.L4_pos_100V_measurement.setEnabled(True)
                self.L4_pos_100V_measurement.setFocus()

        # Disable the other buttons
        for button in self.hv_buttons:
            if button == self.test_pos_100V_btn:
                continue
            else:
                button.setEnabled(False)

        # Enable and set the voltage
        voltage: str = self.test_voltages[0]  # '100'
        hv_enabled: bool = self.get_hv_enable_state()
        if not hv_enabled:
            self.hvps.enable_high_voltage()
        self.hvps.set_voltage(self.channel, voltage)

    def handle_test_pos_500V_btn(self) -> None:
        """
        Tests the selected channel at 500 V
        """
        # Enable the QLineEdit
        match self.channel:
            case 'BM':
                self.beam_pos_500V_measurement.setEnabled(True)
                self.beam_pos_500V_measurement.setFocus()
            case 'EX':
                self.ext_pos_500V_measurement.setEnabled(True)
                self.ext_pos_500V_measurement.setFocus()
            case 'L1':
                self.L1_pos_500V_measurement.setEnabled(True)
                self.L1_pos_500V_measurement.setFocus()
            case 'L2':
                self.L2_pos_500V_measurement.setEnabled(True)
                self.L2_pos_500V_measurement.setFocus()
            case 'L3':
                self.L3_pos_500V_measurement.setEnabled(True)
                self.L3_pos_500V_measurement.setFocus()
            case 'L4':
                self.L4_pos_500V_measurement.setEnabled(True)
                self.L4_pos_500V_measurement.setFocus()

        # Disable the other buttons
        for button in self.hv_buttons:
            if button == self.test_pos_500V_btn:
                continue
            else:
                button.setEnabled(False)

        # Enable and set the voltage
        voltage: str = self.test_voltages[1]  # '500'
        hv_enabled: bool = self.get_hv_enable_state()
        if not hv_enabled:
            self.hvps.enable_high_voltage()
        self.hvps.set_voltage(self.channel, voltage)

    def handle_test_pos_1kV_btn(self) -> None:
        """
        Tests the selected channel at 1000 V
        """
        # Enable the QLineEdit
        match self.channel:
            case 'BM':
                self.beam_pos_1kV_measurement.setEnabled(True)
                self.beam_pos_1kV_measurement.setFocus()
            case 'EX':
                self.ext_pos_1kV_measurement.setEnabled(True)
                self.ext_pos_1kV_measurement.setFocus()
            case 'L1':
                self.L1_pos_1kV_measurement.setEnabled(True)
                self.L1_pos_1kV_measurement.setFocus()
            case 'L2':
                self.L2_pos_1kV_measurement.setEnabled(True)
                self.L2_pos_1kV_measurement.setFocus()
            case 'L3':
                self.L3_pos_1kV_measurement.setEnabled(True)
                self.L3_pos_1kV_measurement.setFocus()
            case 'L4':
                self.L4_pos_1kV_measurement.setEnabled(True)
                self.L4_pos_1kV_measurement.setFocus()

        # Disable the other buttons
        for button in self.hv_buttons:
            if button == self.test_pos_1kV_btn:
                continue
            else:
                button.setEnabled(False)

        # Enable and set the voltage
        voltage: str = self.test_voltages[2]  # '1000'
        hv_enabled: bool = self.get_hv_enable_state()
        if not hv_enabled:
            self.hvps.enable_high_voltage()
        self.hvps.set_voltage(self.channel, voltage)

    def handle_test_neg_100V_btn(self) -> None:
        """
        Tests the selected channel at -100 V
        """
        # Enable the QLineEdit
        match self.channel:
            case 'BM':
                self.beam_neg_100V_measurement.setEnabled(True)
                self.beam_neg_100V_measurement.setFocus()
            case 'EX':
                self.ext_neg_100V_measurement.setEnabled(True)
                self.ext_neg_100V_measurement.setFocus()
            case 'L1':
                self.L1_neg_100V_measurement.setEnabled(True)
                self.L1_neg_100V_measurement.setFocus()
            case 'L2':
                self.L2_neg_100V_measurement.setEnabled(True)
                self.L2_neg_100V_measurement.setFocus()
            case 'L3':
                self.L3_neg_100V_measurement.setEnabled(True)
                self.L3_neg_100V_measurement.setFocus()
            case 'L4':
                self.L4_neg_100V_measurement.setEnabled(True)
                self.L4_neg_100V_measurement.setFocus()

        # Disable the other buttons
        for button in self.hv_buttons:
            if button == self.test_neg_100V_btn:
                continue
            else:
                button.setEnabled(False)

        # Enable and set the voltage
        voltage: str = f'-{self.test_voltages[0]}'  # '-100'
        hv_enabled: bool = self.get_hv_enable_state()
        if not hv_enabled:
            self.hvps.enable_high_voltage()
        self.hvps.set_voltage(self.channel, voltage)

    def handle_test_neg_500V_btn(self) -> None:
        """
        Tests the selected channel at -500 V
        """
        # Enable the QLineEdit
        match self.channel:
            case 'BM':
                self.beam_neg_500V_measurement.setEnabled(True)
                self.beam_neg_500V_measurement.setFocus()
            case 'EX':
                self.ext_neg_500V_measurement.setEnabled(True)
                self.ext_neg_500V_measurement.setFocus()
            case 'L1':
                self.L1_neg_500V_measurement.setEnabled(True)
                self.L1_neg_500V_measurement.setFocus()
            case 'L2':
                self.L2_neg_500V_measurement.setEnabled(True)
                self.L2_neg_500V_measurement.setFocus()
            case 'L3':
                self.L3_neg_500V_measurement.setEnabled(True)
                self.L3_neg_500V_measurement.setFocus()
            case 'L4':
                self.L4_neg_500V_measurement.setEnabled(True)
                self.L4_neg_500V_measurement.setFocus()

        # Disable the other buttons
        for button in self.hv_buttons:
            if button == self.test_neg_500V_btn:
                continue
            else:
                button.setEnabled(False)

        # Enable and set the voltage
        voltage: str = f'-{self.test_voltages[1]}'  # '-500'
        hv_enabled: bool = self.get_hv_enable_state()
        if not hv_enabled:
            self.hvps.enable_high_voltage()
        self.hvps.set_voltage(self.channel, voltage)

    def handle_test_neg_1kV_btn(self) -> None:
        """
        Tests the selected channel at -1000 V
        """
        # Enable the QLineEdit
        match self.channel:
            case 'BM':
                self.beam_neg_1kV_measurement.setEnabled(True)
                self.beam_neg_1kV_measurement.setFocus()
            case 'EX':
                self.ext_neg_1kV_measurement.setEnabled(True)
                self.ext_neg_1kV_measurement.setFocus()
            case 'L1':
                self.L1_neg_1kV_measurement.setEnabled(True)
                self.L1_neg_1kV_measurement.setFocus()
            case 'L2':
                self.L2_neg_1kV_measurement.setEnabled(True)
                self.L2_neg_1kV_measurement.setFocus()
            case 'L3':
                self.L3_neg_1kV_measurement.setEnabled(True)
                self.L3_neg_1kV_measurement.setFocus()
            case 'L4':
                self.L4_neg_1kV_measurement.setEnabled(True)
                self.L4_neg_1kV_measurement.setFocus()

        # Disable the other buttons
        for button in self.hv_buttons:
            if button == self.test_neg_1kV_btn:
                continue
            else:
                button.setEnabled(False)

        # Enable and set the voltage
        voltage: str = f'-{self.test_voltages[2]}'  # '-1000'
        hv_enabled: bool = self.get_hv_enable_state()
        if not hv_enabled:
            self.hvps.enable_high_voltage()
        self.hvps.set_voltage(self.channel, voltage)

    # Create the current test button handlers
    def handle_test_sol_current1_btn(self) -> None:
        """
        Tests the solenoid at 0.3 A
        """
        self.current1_measurement.setEnabled(True)
        self.current1_measurement.setFocus()
        current: str = self.test_currents[0]  # '0.3'
        sol_enabled: bool = self.get_sol_enable_state()
        if not sol_enabled:
            self.hvps.enable_solenoid_current()
        self.hvps.set_solenoid_current(current)

    def handle_test_sol_current2_btn(self) -> None:
        """
        Tests the solenoid at 1.2 A
        """
        self.current2_measurement.setEnabled(True)
        self.current2_measurement.setFocus()
        current: str = self.test_currents[1]  # '1.2'
        sol_enabled: bool = self.get_sol_enable_state()
        if not sol_enabled:
            self.hvps.enable_solenoid_current()
        self.hvps.set_solenoid_current(current)

    def handle_test_sol_current3_btn(self) -> None:
        """
        Tests the solenoid at 2.5 A
        """
        self.current3_measurement.setEnabled(True)
        self.current3_measurement.setFocus()
        current: str = self.test_currents[2]  # '2.5'
        sol_enabled: bool = self.get_sol_enable_state()
        if not sol_enabled:
            self.hvps.enable_solenoid_current()
        self.hvps.set_solenoid_current(current)

    # Create the Beam pressReturn event handlers
    def handle_beam_pos_100V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.beam_pos_100V_measurement.text()
        self.channel_readbacks[0] = readback
        self.channel_measurements[0] = measurement
        self.beam_pos_100V_measurement.setEnabled(False)
        self.beam_pos_100V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_pos_500V_btn.setFocus()

    def handle_beam_pos_500V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.beam_pos_500V_measurement.text()
        self.channel_readbacks[1] = readback
        self.channel_measurements[1] = measurement
        self.beam_pos_500V_measurement.setEnabled(False)
        self.beam_pos_500V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_pos_1kV_btn.setFocus()

    def handle_beam_pos_1kV_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.beam_pos_1kV_measurement.text()
        self.channel_readbacks[2] = readback
        self.channel_measurements[2] = measurement
        self.beam_pos_1kV_measurement.setEnabled(False)
        self.beam_pos_1kV_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_neg_100V_btn.setFocus()

    def handle_beam_neg_100V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.beam_neg_100V_measurement.text()
        self.channel_readbacks[3] = readback
        self.channel_measurements[3] = measurement
        self.beam_neg_100V_measurement.setEnabled(False)
        self.beam_neg_100V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_neg_500V_btn.setFocus()

    def handle_beam_neg_500V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.beam_neg_500V_measurement.text()
        self.channel_readbacks[4] = readback
        self.channel_measurements[4] = measurement
        self.beam_neg_500V_measurement.setEnabled(False)
        self.beam_neg_500V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_neg_1kV_btn.setFocus()

    def handle_beam_neg_1kV_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.beam_neg_1kV_measurement.text()
        self.channel_readbacks[5] = readback
        self.channel_measurements[5] = measurement
        self.beam_neg_1kV_measurement.setEnabled(False)
        self.beam_neg_1kV_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.next_btn.setFocus()

    # Create the Extractor pressReturn event handlers
    def handle_ext_pos_100V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.ext_pos_100V_measurement.text()
        self.channel_readbacks[0] = readback
        self.channel_measurements[0] = measurement
        self.ext_pos_100V_measurement.setEnabled(False)
        self.ext_pos_100V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_pos_500V_btn.setFocus()

    def handle_ext_pos_500V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.ext_pos_500V_measurement.text()
        self.channel_readbacks[1] = readback
        self.channel_measurements[1] = measurement
        self.ext_pos_500V_measurement.setEnabled(False)
        self.ext_pos_500V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_pos_1kV_btn.setFocus()

    def handle_ext_pos_1kV_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.ext_pos_1kV_measurement.text()
        self.channel_readbacks[2] = readback
        self.channel_measurements[2] = measurement
        self.ext_pos_1kV_measurement.setEnabled(False)
        self.ext_pos_1kV_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_neg_100V_btn.setFocus()

    def handle_ext_neg_100V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.ext_neg_100V_measurement.text()
        self.channel_readbacks[3] = readback
        self.channel_measurements[3] = measurement
        self.ext_neg_100V_measurement.setEnabled(False)
        self.ext_neg_100V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_neg_500V_btn.setFocus()

    def handle_ext_neg_500V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.ext_neg_500V_measurement.text()
        self.channel_readbacks[4] = readback
        self.channel_measurements[4] = measurement
        self.ext_neg_500V_measurement.setEnabled(False)
        self.ext_neg_500V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_neg_1kV_btn.setFocus()

    def handle_ext_neg_1kV_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.ext_neg_1kV_measurement.text()
        self.channel_readbacks[5] = readback
        self.channel_measurements[5] = measurement
        self.ext_neg_1kV_measurement.setEnabled(False)
        self.ext_neg_1kV_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.next_btn.setFocus()

    # Create the L1 pressReturn event handler
    def handle_L1_pos_100V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L1_pos_100V_measurement.text()
        self.channel_readbacks[0] = readback
        self.channel_measurements[0] = measurement
        self.L1_pos_100V_measurement.setEnabled(False)
        self.L1_pos_100V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_pos_500V_btn.setFocus()

    def handle_L1_pos_500V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L1_pos_500V_measurement.text()
        self.channel_readbacks[1] = readback
        self.channel_measurements[1] = measurement
        self.L1_pos_500V_measurement.setEnabled(False)
        self.L1_pos_500V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_pos_1kV_btn.setFocus()

    def handle_L1_pos_1kV_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L1_pos_1kV_measurement.text()
        self.channel_readbacks[2] = readback
        self.channel_measurements[2] = measurement
        self.L1_pos_1kV_measurement.setEnabled(False)
        self.L1_pos_1kV_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_neg_100V_btn.setFocus()

    def handle_L1_neg_100V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L1_neg_100V_measurement.text()
        self.channel_readbacks[3] = readback
        self.channel_measurements[3] = measurement
        self.L1_neg_100V_measurement.setEnabled(False)
        self.L1_neg_100V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_neg_500V_btn.setFocus()

    def handle_L1_neg_500V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L1_neg_500V_measurement.text()
        self.channel_readbacks[4] = readback
        self.channel_measurements[4] = measurement
        self.L1_neg_500V_measurement.setEnabled(False)
        self.L1_neg_500V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_neg_1kV_btn.setFocus()

    def handle_L1_neg_1kV_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L1_neg_1kV_measurement.text()
        self.channel_readbacks[5] = readback
        self.channel_measurements[5] = measurement
        self.L1_neg_1kV_measurement.setEnabled(False)
        self.L1_neg_1kV_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.next_btn.setFocus()

    # Create the L2 pressReturn event handler
    def handle_L2_pos_100V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L2_pos_100V_measurement.text()
        self.channel_readbacks[0] = readback
        self.channel_measurements[0] = measurement
        self.L2_pos_100V_measurement.setEnabled(False)
        self.L2_pos_100V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_pos_500V_btn.setFocus()

    def handle_L2_pos_500V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L2_pos_500V_measurement.text()
        self.channel_readbacks[1] = readback
        self.channel_measurements[1] = measurement
        self.L2_pos_500V_measurement.setEnabled(False)
        self.L2_pos_500V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_pos_1kV_btn.setFocus()

    def handle_L2_pos_1kV_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L2_pos_1kV_measurement.text()
        self.channel_readbacks[2] = readback
        self.channel_measurements[2] = measurement
        self.L2_pos_1kV_measurement.setEnabled(False)
        self.L2_pos_1kV_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_neg_100V_btn.setFocus()

    def handle_L2_neg_100V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L2_neg_100V_measurement.text()
        self.channel_readbacks[3] = readback
        self.channel_measurements[3] = measurement
        self.L2_neg_100V_measurement.setEnabled(False)
        self.L2_neg_100V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_neg_500V_btn.setFocus()

    def handle_L2_neg_500V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L2_neg_500V_measurement.text()
        self.channel_readbacks[4] = readback
        self.channel_measurements[4] = measurement
        self.L2_neg_500V_measurement.setEnabled(False)
        self.L2_neg_500V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_neg_1kV_btn.setFocus()

    def handle_L2_neg_1kV_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L2_neg_1kV_measurement.text()
        self.channel_readbacks[5] = readback
        self.channel_measurements[5] = measurement
        self.L2_neg_1kV_measurement.setEnabled(False)
        self.L2_neg_1kV_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.next_btn.setFocus()

    # Create the L3 pressReturn event handler
    def handle_L3_pos_100V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L3_pos_100V_measurement.text()
        self.channel_readbacks[0] = readback
        self.channel_measurements[0] = measurement
        self.L3_pos_100V_measurement.setEnabled(False)
        self.L3_pos_100V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_pos_500V_btn.setFocus()

    def handle_L3_pos_500V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L3_pos_500V_measurement.text()
        self.channel_readbacks[1] = readback
        self.channel_measurements[1] = measurement
        self.L3_pos_500V_measurement.setEnabled(False)
        self.L3_pos_500V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_pos_1kV_btn.setFocus()

    def handle_L3_pos_1kV_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L3_pos_1kV_measurement.text()
        self.channel_readbacks[2] = readback
        self.channel_measurements[2] = measurement
        self.L3_pos_1kV_measurement.setEnabled(False)
        self.L3_pos_1kV_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_neg_100V_btn.setFocus()

    def handle_L3_neg_100V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L3_neg_100V_measurement.text()
        self.channel_readbacks[3] = readback
        self.channel_measurements[3] = measurement
        self.L3_neg_100V_measurement.setEnabled(False)
        self.L3_neg_100V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_neg_500V_btn.setFocus()

    def handle_L3_neg_500V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L3_neg_500V_measurement.text()
        self.channel_readbacks[4] = readback
        self.channel_measurements[4] = measurement
        self.L3_neg_500V_measurement.setEnabled(False)
        self.L3_neg_500V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_neg_1kV_btn.setFocus()

    def handle_L3_neg_1kV_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L3_neg_1kV_measurement.text()
        self.channel_readbacks[5] = readback
        self.channel_measurements[5] = measurement
        self.L3_neg_1kV_measurement.setEnabled(False)
        self.L3_neg_1kV_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.next_btn.setFocus()

    # Create the L4 pressReturn event handler
    def handle_L4_pos_100V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L4_pos_100V_measurement.text()
        self.channel_readbacks[0] = readback
        self.channel_measurements[0] = measurement
        self.L4_pos_100V_measurement.setEnabled(False)
        self.L4_pos_100V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_pos_500V_btn.setFocus()

    def handle_L4_pos_500V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L4_pos_500V_measurement.text()
        self.channel_readbacks[1] = readback
        self.channel_measurements[1] = measurement
        self.L4_pos_500V_measurement.setEnabled(False)
        self.L4_pos_500V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_pos_1kV_btn.setFocus()

    def handle_L4_pos_1kV_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L4_pos_1kV_measurement.text()
        self.channel_readbacks[2] = readback
        self.channel_measurements[2] = measurement
        self.L4_pos_1kV_measurement.setEnabled(False)
        self.L4_pos_1kV_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_neg_100V_btn.setFocus()

    def handle_L4_neg_100V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L4_neg_100V_measurement.text()
        self.channel_readbacks[3] = readback
        self.channel_measurements[3] = measurement
        self.L4_neg_100V_measurement.setEnabled(False)
        self.L4_neg_100V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_neg_500V_btn.setFocus()

    def handle_L4_neg_500V_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L4_neg_500V_measurement.text()
        self.channel_readbacks[4] = readback
        self.channel_measurements[4] = measurement
        self.L4_neg_500V_measurement.setEnabled(False)
        self.L4_neg_500V_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.test_neg_1kV_btn.setFocus()

    def handle_L4_neg_1kV_entered(self) -> None:
        readback: str = self.hvps.get_voltage(self.channel)
        measurement: str = self.L4_neg_1kV_measurement.text()
        self.channel_readbacks[5] = readback
        self.channel_measurements[5] = measurement
        self.L4_neg_1kV_measurement.setEnabled(False)
        self.L4_neg_1kV_measurement.clearFocus()
        self.hvps.set_voltage(self.channel, '0')
        self.hvps.disable_high_voltage()
        for button in self.hv_buttons:
            button.setEnabled(True)
        self.next_btn.setFocus()

    # Create the Solenoid pressReturn event handler
    def handle_current1_entered(self) -> None:
        readback: str = self.hvps.get_current(self.channel)
        measurement: str = self.current1_measurement.text()
        self.channel_readbacks[0] = readback
        self.channel_measurements[0] = measurement
        self.current1_measurement.setEnabled(False)
        self.current1_measurement.clearFocus()
        self.hvps.set_solenoid_current('0')
        self.hvps.disable_solenoid_current()
        for button in self.current_buttons:
            button.setEnabled(True)
        self.current2_btn.setFocus()

    def handle_current2_entered(self) -> None:
        readback: str = self.hvps.get_current(self.channel)
        measurement: str = self.current2_measurement.text()
        self.channel_readbacks[1] = readback
        self.channel_measurements[1] = measurement
        self.current2_measurement.setEnabled(False)
        self.current2_measurement.clearFocus()
        self.hvps.set_solenoid_current('0')
        self.hvps.disable_solenoid_current()
        for button in self.current_buttons:
            button.setEnabled(True)
        self.current3_btn.setFocus()

    def handle_current3_entered(self) -> None:
        readback: str = self.hvps.get_current(self.channel)
        measurement: str = self.current3_measurement.text()
        self.channel_readbacks[2] = readback
        self.channel_measurements[2] = measurement
        self.current3_measurement.setEnabled(False)
        self.current3_measurement.clearFocus()
        self.hvps.set_solenoid_current('0')
        self.hvps.disable_solenoid_current()
        for button in self.current_buttons:
            button.setEnabled(True)
        self.next_btn.setFocus()

    # DELETE IF THE SPECIFIC HANDLERS WORK
    # def handle_test_sol_btn(self, current: str) -> None:
    #     """
    #     Checks if the solenoid enable state. If it is not on, enables the solenoid.
    #     Sets the solenoid current target to the specified current.
    #     """
    #     if self.get_sol_enable_state() is False:
    #         self.hvps.enable_solenoid_current()
    #     self.hvps.set_solenoid_current(current)

    # def handle_voltage_returnPressed(self, measurement: str, widget: QLineEdit) -> None:
    #     """
    #     Gets the readback value of the voltage for the current channel.
    #     Appends the readback value to the channel_readbacks list.
    #     Appends the value in the QLineEdit to the channel_measurements list.
    #     """
    #     print(
    #         f'[RETURN PRESSED] Measurement: {measurement}, clearing voltage for {self.channel}'
    #     )
    #     readback = self.hvps.get_voltage(self.channel)
    #     self.channel_readbacks.append(readback)
    #     self.channel_measurements.append(measurement)
    #     widget.setEnabled(False)
    #     widget.clearFocus()
    #     self.hvps.set_voltage(self.channel, '0')
    #     self.hvps.disable_high_voltage()

    # def handle_current_returnPressed(self, measurement: str, widget: QLineEdit) -> None:
    #     """
    #     Gets the readback value of the solenoid current.
    #     Appends the readback value to the channel_readbacks list
    #     Appends the value in the QLineEdit to the channel_measurements list.
    #     """
    #     print('Return Pressed!')
    #     readback = self.hvps.get_current('SL')
    #     self.channel_readbacks.append(readback)
    #     self.channel_measurements.append(measurement)
    #     self.hvps.set_solenoid_current('0')
    #     widget.setEnabled(False)
    #     widget.clearFocus()

    # def handle_test_hv_btn(self, voltage: str) -> None:
    #     """
    #     Checks the HV enable state. If it is not on, enables the HV.
    #     Sets the current channel HV target to the specified voltage.
    #     """
    #     print(f'[BUTTON PRESSED] Setting voltage {voltage} on {self.channel}')
    #     traceback.print_stack(limit=5)
    #     if self.get_hv_enable_state() is False:
    #         self.hvps.enable_high_voltage()
    #     self.hvps.set_voltage(self.channel, voltage)


# if __name__ == '__main__':
#     import sys

#     from PySide6.QtWidgets import QApplication

#     from src.pdf import HVPSReport

#     def create_pdf(readbacks, measurements):
#         pdf = HVPSReport(
#             'SN-XXX',
#             ['BM', 'EX', 'L1', 'L2', 'L3', 'L4', 'SL'],
#             readbacks,
#             measurements,
#         )
#         pdf.open()

#     version = '1.0.0'
#     app = QApplication([])
#     window = HVPSTestWindow(
#         hvps=HVPSv3(sock=None),
#         occupied_channels=['BM', 'EX', 'L1', 'L2', 'L3', 'L4', 'SL'],
#     )
#     window.test_complete.connect(create_pdf)
#     window.show()
#     sys.exit(app.exec())
