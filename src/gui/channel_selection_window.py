from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGridLayout,
    QLineEdit,
    QPushButton,
)


class ChannelSelectionWindow(QDialog):
    """
    Creates a gui window that will allow the user to select which channels
    are installed into the HVPSv3. Emits a Signal with list of occupied channels.
    """

    channels_selected = Signal(list)
    serial_number_entered = Signal(str)
    window_closed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog)
        self.create_gui()

    def create_gui(self) -> None:
        """
        Creates the checkbox widgets for the user to select which channels
        are occupied in the HVPS.
        """
        window_width = 280
        window_height = 200
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Select Installed Channels')
        self.occupied_channels: list = []
        self.serial_number: str = ''

        # Create the serial number QLineEdit
        self.serial_number_entry = QLineEdit(placeholderText='Enter HVPS Serial Number')

        # Create the checkboxes
        beam_channel_chbx = QCheckBox('Beam')
        ext_channel_chbx = QCheckBox('Extractor')
        L1_channel_chbx = QCheckBox('Lens 1')
        L2_channel_chbx = QCheckBox('Lens 2')
        L3_channel_chbx = QCheckBox('Lens 3')
        L4_channel_chbx = QCheckBox('Lens 4')
        sol_channel_chbx = QCheckBox('Solenoid')

        # Set the most commonly used channels to be automatically checked.
        beam_channel_chbx.setChecked(True)
        ext_channel_chbx.setChecked(True)
        L1_channel_chbx.setChecked(True)
        sol_channel_chbx.setChecked(True)

        # Create a dict of the checkboxes and the associated channel names.
        self.checkbox_channels: dict[QCheckBox, str] = {
            beam_channel_chbx: 'BM',
            ext_channel_chbx: 'EX',
            L1_channel_chbx: 'L1',
            L2_channel_chbx: 'L2',
            L3_channel_chbx: 'L3',
            L4_channel_chbx: 'L4',
            sol_channel_chbx: 'SL',
        }

        # Create the `Ok`` button
        channel_select_btn = QPushButton('Ok')
        channel_select_btn.clicked.connect(self.handle_ok_btn_clicked)

        # Create the layout
        main_layout = QGridLayout()
        main_layout.addWidget(self.serial_number_entry, 0, 0, 1, 3)
        main_layout.addWidget(beam_channel_chbx, 1, 0)
        main_layout.addWidget(ext_channel_chbx, 2, 0)
        main_layout.addWidget(L1_channel_chbx, 1, 1)
        main_layout.addWidget(L2_channel_chbx, 2, 1)
        main_layout.addWidget(L3_channel_chbx, 1, 2)
        main_layout.addWidget(L4_channel_chbx, 2, 2)
        main_layout.addWidget(sol_channel_chbx, 3, 0)
        main_layout.addWidget(
            channel_select_btn, 4, 0, 1, 3, Qt.AlignmentFlag.AlignCenter
        )

        self.setLayout(main_layout)

    def handle_ok_btn_clicked(self) -> None:
        for chbx, channel in self.checkbox_channels.items():
            if chbx.isChecked():
                self.occupied_channels.append(channel)
        self.serial_number = self.serial_number_entry.text()
        self.channels_selected.emit(self.occupied_channels)
        self.serial_number_entered.emit(self.serial_number)
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.window_closed.emit()
        super().closeEvent(event)
