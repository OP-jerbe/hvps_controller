from pathlib import Path
from socket import SocketType
from typing import Callable

from PySide6.QtCore import QRegularExpression, Qt, Signal
from PySide6.QtGui import (
    QCloseEvent,
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


class ChannelSelectionWindow(QDialog):
    """
    Class to create a gui window that will allow the user to select which channels
    are installed into the HVPSv3. Emits a Signal with list of occupied channels.
    """

    channels_selected = Signal(list)

    def __init__(self) -> None:
        self.setWindowFlags(Qt.WindowType.Dialog)
        self.create_gui()

    def create_gui(self) -> None:
        """
        Creates the checkbox widgets for the user to select which channels
        are occupied in the HVPS.
        """
        window_width = 280
        window_height = 180
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle('Select Installed Channels')
        self.occupied_channels: list = []

        # Create the checkboxes
        beam_channel_chbx = QCheckBox('Beam')
        ext_channel_chbx = QCheckBox('Extractor')
        L1_channel_chbx = QCheckBox('Lens 1')
        L2_channel_chbx = QCheckBox('Lens 2')
        L3_channel_chbx = QCheckBox('Lens 3')
        L4_channel_chbx = QCheckBox('Lens 4')
        sol_channel_chbx = QCheckBox('Solenoid')

        # Set the most commonly used channels to be automatically checked\
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

        main_layout = QGridLayout()
        main_layout.addWidget(beam_channel_chbx, 0, 0)
        main_layout.addWidget(ext_channel_chbx, 1, 0)
        main_layout.addWidget(L1_channel_chbx, 0, 1)
        main_layout.addWidget(L2_channel_chbx, 1, 1)
        main_layout.addWidget(L3_channel_chbx, 0, 2)
        main_layout.addWidget(L4_channel_chbx, 1, 2)
        main_layout.addWidget(sol_channel_chbx, 2, 0)
        main_layout.addWidget(
            channel_select_btn, 3, 0, 1, 3, Qt.AlignmentFlag.AlignCenter
        )

        self.setLayout(main_layout)

    def handle_ok_btn_clicked(self) -> None:
        for chbx, channel in self.checkbox_channels.items():
            if chbx.isChecked():
                self.occupied_channels.append(channel)
        self.channels_selected.emit(self.occupied_channels)
