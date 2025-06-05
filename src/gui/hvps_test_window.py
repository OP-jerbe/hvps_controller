from pathlib import Path
from socket import SocketType
from typing import Callable, Optional

from PySide6.QtCore import QEvent, QObject, QRegularExpression, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QIcon,
    QMouseEvent,
    QPixmap,
    QRegularExpressionValidator,
    QTextCursor,
    QTextListFormat,
)
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
    QTextEdit,
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
        self.test_voltage: str = '200'
        self.test_currents: tuple[str, ...] = ('0.3', '1.2', '2.5')
        self.installEventFilter(self)
        self.root_dir: Path = get_root_dir()
        icon_path: str = str(self.root_dir / 'assets' / 'hvps_icon.ico')
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
        self.current_stage_index += 1
        self.load_current_stage()

    def create_beam_test_gui(self) -> None:
        window_width = 1200
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Beam Channel Test')

        instructions: str = (
            '1. Plug HV pigtail into Beam HV recepticle.\n'
            '2. Attach positive lead of voltmeter to pigtail.\n'
            '3. Attach common lead of voltmeter to ground.\n'
            '4. Press the "Enable POS HV" button.\n'
            '5. Verify +200 V on the voltmeter.\n'
            '6. Press the "Enable NEG HV" button.\n'
            '7. Verify -200 V on the voltmeter.\n'
            '8. Press the "Disable HV" button.\n'
            '9. Click the "Next" button to continue.\n'
        )

        title_label = QLabel('Beam Test')
        instructions_txt = QLabel(instructions)

        enable_pos_hv_btn = QPushButton('Enable POS HV')
        enable_pos_hv_btn.clicked.connect(lambda: self.handle_enable_pos_hv_btn('BM'))

        enable_neg_hv_btn = QPushButton('Enable NEG HV')
        enable_neg_hv_btn.clicked.connect(lambda: self.handle_enable_neg_hv_btn('BM'))

        disable_hv_btn = QPushButton('Disable HV')
        disable_hv_btn.clicked.connect(self.handle_disable_hv_btn)

        next_btn = QPushButton('Next')
        next_btn.clicked.connect(self.handle_next_btn)

        # Create a vertical line
        vertical_line = QFrame()
        vertical_line.setFrameShape(QFrame.Shape.VLine)

        # Create the widget to hold the photo
        photo = QLabel()
        photo_path: Path = self.root_dir / 'assets' / 'beam.jpg'
        pixmap = QPixmap(photo_path)
        photo.setPixmap(pixmap)

        self.main_layout.addWidget(title_label, 0, 0, 1, 2)
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 3)
        self.main_layout.addWidget(enable_pos_hv_btn, 2, 0)
        self.main_layout.addWidget(enable_neg_hv_btn, 2, 1)
        self.main_layout.addWidget(disable_hv_btn, 2, 2)
        self.main_layout.addWidget(next_btn, 3, 0, 1, 3)

        self.main_layout.addWidget(vertical_line, 0, 3, 4, 1)

        self.main_layout.addWidget(photo, 0, 4, 4, 1)
        self.setLayout(self.main_layout)

    def create_ext_test_gui(self) -> None:
        window_width = 1200
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Extractor Channel Test')

        instructions: str = (
            '1. Plug HV pigtail into Extractor HV recepticle.\n'
            '2. Attach positive lead of voltmeter to pigtail.\n'
            '3. Attach common lead of voltmeter to ground.\n'
            '4. Press the "Enable POS HV" button.\n'
            '5. Verify +200 V on the voltmeter.\n'
            '6. Press the "Enable NEG HV" button.\n'
            '7. Verify -200 V on the voltmeter.\n'
            '8. Press the "Disable HV" button.\n'
            '9. Click the "Next" button to continue.\n'
        )

        title_label = QLabel('Extractor Test')
        instructions_txt = QLabel(instructions)

        enable_pos_hv_btn = QPushButton('Enable POS HV')
        enable_pos_hv_btn.clicked.connect(lambda: self.handle_enable_pos_hv_btn('EX'))

        enable_neg_hv_btn = QPushButton('Enable NEG HV')
        enable_neg_hv_btn.clicked.connect(lambda: self.handle_enable_neg_hv_btn('EX'))

        disable_hv_btn = QPushButton('Disable HV')
        disable_hv_btn.clicked.connect(self.handle_disable_hv_btn)

        next_btn = QPushButton('Next')
        next_btn.clicked.connect(self.handle_next_btn)

        # Create a vertical line
        vertical_line = QFrame()
        vertical_line.setFrameShape(QFrame.Shape.VLine)

        # Create the widget to hold the photo
        photo = QLabel()
        photo_path: Path = self.root_dir / 'assets' / 'ext.jpg'
        pixmap = QPixmap(photo_path)
        photo.setPixmap(pixmap)

        self.main_layout.addWidget(title_label, 0, 0, 1, 2)
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 3)
        self.main_layout.addWidget(enable_pos_hv_btn, 2, 0)
        self.main_layout.addWidget(enable_neg_hv_btn, 2, 1)
        self.main_layout.addWidget(disable_hv_btn, 2, 2)
        self.main_layout.addWidget(next_btn, 3, 0, 1, 3)

        self.main_layout.addWidget(vertical_line, 0, 3, 4, 1)

        self.main_layout.addWidget(photo, 0, 4, 4, 1)
        self.setLayout(self.main_layout)

    def create_L1_test_gui(self) -> None:
        window_width = 1200
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Lens 1 Channel Test')

        instructions: str = (
            '1. Plug HV pigtail into Lens 1 HV recepticle.\n'
            '2. Attach positive lead of voltmeter to pigtail.\n'
            '3. Attach common lead of voltmeter to ground.\n'
            '4. Press the "Enable POS HV" button.\n'
            '5. Verify +200 V on the voltmeter.\n'
            '6. Press the "Enable NEG HV" button.\n'
            '7. Verify -200 V on the voltmeter.\n'
            '8. Press the "Disable HV" button.\n'
            '9. Click the "Next" button to continue.\n'
        )

        title_label = QLabel('Lens 1 Test')
        instructions_txt = QLabel(instructions)

        enable_pos_hv_btn = QPushButton('Enable POS HV')
        enable_pos_hv_btn.clicked.connect(lambda: self.handle_enable_pos_hv_btn('L1'))

        enable_neg_hv_btn = QPushButton('Enable NEG HV')
        enable_neg_hv_btn.clicked.connect(lambda: self.handle_enable_neg_hv_btn('L1'))

        disable_hv_btn = QPushButton('Disable HV')
        disable_hv_btn.clicked.connect(self.handle_disable_hv_btn)

        next_btn = QPushButton('Next')
        next_btn.clicked.connect(self.handle_next_btn)

        # Create a vertical line
        vertical_line = QFrame()
        vertical_line.setFrameShape(QFrame.Shape.VLine)

        # Create the widget to hold the photo
        photo = QLabel()
        photo_path: Path = self.root_dir / 'assets' / 'L1.jpg'
        pixmap = QPixmap(photo_path)
        photo.setPixmap(pixmap)

        self.main_layout.addWidget(title_label, 0, 0, 1, 2)
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 3)
        self.main_layout.addWidget(enable_pos_hv_btn, 2, 0)
        self.main_layout.addWidget(enable_neg_hv_btn, 2, 1)
        self.main_layout.addWidget(disable_hv_btn, 2, 2)
        self.main_layout.addWidget(next_btn, 3, 0, 1, 3)

        self.main_layout.addWidget(vertical_line, 0, 3, 4, 1)

        self.main_layout.addWidget(photo, 0, 4, 4, 1)
        self.setLayout(self.main_layout)

    def create_L2_test_gui(self) -> None:
        window_width = 1200
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Lens 2 Channel Test')

        instructions: str = (
            '1. Plug HV pigtail into Lens 2 HV recepticle.\n'
            '2. Attach positive lead of voltmeter to pigtail.\n'
            '3. Attach common lead of voltmeter to ground.\n'
            '4. Press the "Enable POS HV" button.\n'
            '5. Verify +200 V on the voltmeter.\n'
            '6. Press the "Enable NEG HV" button.\n'
            '7. Verify -200 V on the voltmeter.\n'
            '8. Press the "Disable HV" button.\n'
            '9. Click the "Next" button to continue.\n'
        )

        title_label = QLabel('Lens 2 Test')
        instructions_txt = QLabel(instructions)

        enable_pos_hv_btn = QPushButton('Enable POS HV')
        enable_pos_hv_btn.clicked.connect(lambda: self.handle_enable_pos_hv_btn('L2'))

        enable_neg_hv_btn = QPushButton('Enable NEG HV')
        enable_neg_hv_btn.clicked.connect(lambda: self.handle_enable_neg_hv_btn('L2'))

        disable_hv_btn = QPushButton('Disable HV')
        disable_hv_btn.clicked.connect(self.handle_disable_hv_btn)

        next_btn = QPushButton('Next')
        next_btn.clicked.connect(self.handle_next_btn)

        # Create a vertical line
        vertical_line = QFrame()
        vertical_line.setFrameShape(QFrame.Shape.VLine)

        # Create the widget to hold the photo
        photo = QLabel()
        photo_path: Path = self.root_dir / 'assets' / 'L2.jpg'
        pixmap = QPixmap(photo_path)
        photo.setPixmap(pixmap)

        self.main_layout.addWidget(title_label, 0, 0, 1, 2)
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 3)
        self.main_layout.addWidget(enable_pos_hv_btn, 2, 0)
        self.main_layout.addWidget(enable_neg_hv_btn, 2, 1)
        self.main_layout.addWidget(disable_hv_btn, 2, 2)
        self.main_layout.addWidget(next_btn, 3, 0, 1, 3)

        self.main_layout.addWidget(vertical_line, 0, 3, 4, 1)

        self.main_layout.addWidget(photo, 0, 4, 4, 1)
        self.setLayout(self.main_layout)

    def create_L3_test_gui(self) -> None:
        window_width = 1200
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Lens 3 Channel Test')

        instructions: str = (
            '1. Plug HV pigtail into Lens 3 HV recepticle.\n'
            '2. Attach positive lead of voltmeter to pigtail.\n'
            '3. Attach common lead of voltmeter to ground.\n'
            '4. Press the "Enable POS HV" button.\n'
            '5. Verify +200 V on the voltmeter.\n'
            '6. Press the "Enable NEG HV" button.\n'
            '7. Verify -200 V on the voltmeter.\n'
            '8. Press the "Disable HV" button.\n'
            '9. Click the "Next" button to continue.\n'
        )

        title_label = QLabel('Lens 3 Test')
        instructions_txt = QLabel(instructions)

        enable_pos_hv_btn = QPushButton('Enable POS HV')
        enable_pos_hv_btn.clicked.connect(lambda: self.handle_enable_pos_hv_btn('L3'))

        enable_neg_hv_btn = QPushButton('Enable NEG HV')
        enable_neg_hv_btn.clicked.connect(lambda: self.handle_enable_neg_hv_btn('L3'))

        disable_hv_btn = QPushButton('Disable HV')
        disable_hv_btn.clicked.connect(self.handle_disable_hv_btn)

        next_btn = QPushButton('Next')
        next_btn.clicked.connect(self.handle_next_btn)

        # Create a vertical line
        vertical_line = QFrame()
        vertical_line.setFrameShape(QFrame.Shape.VLine)

        # Create the widget to hold the photo
        photo = QLabel()
        photo_path: Path = self.root_dir / 'assets' / 'L3.jpg'
        pixmap = QPixmap(photo_path)
        photo.setPixmap(pixmap)

        self.main_layout.addWidget(title_label, 0, 0, 1, 2)
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 3)
        self.main_layout.addWidget(enable_pos_hv_btn, 2, 0)
        self.main_layout.addWidget(enable_neg_hv_btn, 2, 1)
        self.main_layout.addWidget(disable_hv_btn, 2, 2)
        self.main_layout.addWidget(next_btn, 3, 0, 1, 3)

        self.main_layout.addWidget(vertical_line, 0, 3, 4, 1)

        self.main_layout.addWidget(photo, 0, 4, 4, 1)
        self.setLayout(self.main_layout)

    def create_L4_test_gui(self) -> None:
        window_width = 1200
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Lens 4 Channel Test')

        instructions: str = (
            '1. Plug HV pigtail into Lens 4 HV recepticle.\n'
            '2. Attach positive lead of voltmeter to pigtail.\n'
            '3. Attach common lead of voltmeter to ground.\n'
            '4. Press the "Enable POS HV" button.\n'
            '5. Verify +200 V on the voltmeter.\n'
            '6. Press the "Enable NEG HV" button.\n'
            '7. Verify -200 V on the voltmeter.\n'
            '8. Press the "Disable HV" button.\n'
            '9. Click the "Next" button to continue.\n'
        )

        title_label = QLabel('Lens 4 Test')
        instructions_txt = QLabel(instructions)

        enable_pos_hv_btn = QPushButton('Enable POS HV')
        enable_pos_hv_btn.clicked.connect(lambda: self.handle_enable_pos_hv_btn('L4'))

        enable_neg_hv_btn = QPushButton('Enable NEG HV')
        enable_neg_hv_btn.clicked.connect(lambda: self.handle_enable_neg_hv_btn('L4'))

        disable_hv_btn = QPushButton('Disable HV')
        disable_hv_btn.clicked.connect(self.handle_disable_hv_btn)

        next_btn = QPushButton('Next')
        next_btn.clicked.connect(self.handle_next_btn)

        # Create a vertical line
        vertical_line = QFrame()
        vertical_line.setFrameShape(QFrame.Shape.VLine)

        # Create the widget to hold the photo
        photo = QLabel()
        photo_path: Path = self.root_dir / 'assets' / 'L4.jpg'
        pixmap = QPixmap(photo_path)
        photo.setPixmap(pixmap)

        self.main_layout.addWidget(title_label, 0, 0, 1, 2)
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 3)
        self.main_layout.addWidget(enable_pos_hv_btn, 2, 0)
        self.main_layout.addWidget(enable_neg_hv_btn, 2, 1)
        self.main_layout.addWidget(disable_hv_btn, 2, 2)
        self.main_layout.addWidget(next_btn, 3, 0, 1, 3)

        self.main_layout.addWidget(vertical_line, 0, 3, 4, 1)

        self.main_layout.addWidget(photo, 0, 4, 4, 1)
        self.setLayout(self.main_layout)

    def create_sol_test_gui(self) -> None:
        window_width = 1200
        window_height = 600
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Solenoid Channel Test')

        instructions: str = (
            '1.  Plug in a 2-pin Fischer connector to the solenoid current recepticle.\n'
            '2.  Plug in the current tester connector to other end of the 2-pin\n'
            '     Fischer connector.\n'
            '3.  Set up a multimeter to measure current. Set the scale to so that\n'
            '     the meter can read up to 2.5 A.\n'
            '4.  Attach the positive lead to one pin of the current connector.\n'
            '5.  Attach the common lead to the other pin of the current connector.\n'
            '6.  Press the "Test 0.3 A" button.\n'
            '7.  Verify 0.3 A on the ammeter.\n'
            '8.  Press the "Test 1.2 A" button.\n'
            '9.  Verify 1.2 A on the ammeter.\n'
            '10. Press the "2.5 A" button.\n'
            '11. Verify 2.5 A on the ammeter.\n'
            '12. Press the "Disable Solenoid" button.\n'
        )

        title_label = QLabel('Solenoid Test')
        instructions_txt = QLabel(instructions)

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

        self.main_layout.addWidget(title_label, 0, 0, 1, 3)
        self.main_layout.addWidget(instructions_txt, 1, 0, 1, 3)
        self.main_layout.addWidget(current1_btn, 2, 0)
        self.main_layout.addWidget(current2_btn, 2, 1)
        self.main_layout.addWidget(current3_btn, 2, 2)
        self.main_layout.addWidget(disable_sol_btn, 3, 0, 1, 3)
        self.main_layout.addWidget(next_btn, 4, 0, 1, 3)

        self.main_layout.addWidget(vertical_line, 0, 4, 5, 1)

        self.main_layout.addWidget(photo, 0, 5, 5, 1)
        self.setLayout(self.main_layout)

    def handle_disable_hv_btn(self) -> None:
        self.hvps.disable_high_voltage()

    def handle_enable_pos_hv_btn(self, channel: str) -> None:
        voltage: str = f'{self.test_voltage}'
        self.hvps.enable_high_voltage()
        self.hvps.set_voltage(channel, voltage)

    def handle_enable_neg_hv_btn(self, channel: str) -> None:
        voltage: str = f'-{self.test_voltage}'
        self.hvps.enable_high_voltage()
        self.hvps.set_voltage(channel, voltage)

    def handle_test_sol_btn(self, current: str) -> None:
        self.hvps.enable_solenoid_current()
        self.hvps.set_solenoid_current(current)

    def handle_disable_sol_btn(self) -> None:
        self.hvps.disable_solenoid_current()

    def closeEvent(self, event) -> None:
        self.window_closed.emit()
        super().closeEvent(event)
