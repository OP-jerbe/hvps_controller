from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from qt_material import apply_stylesheet

from helpers.helpers import get_root_dir


class ChangeSNWindow(QWidget):
    SN_changed = Signal(str)
    window_closed = Signal()

    def __init__(self, current_sn: str, parent=None) -> None:
        """
        Inherits from the QWidget class but sets the window type to Dialog so that the
        icon appears in the title bar. Allows the user to change the serial number
        of the HVPS being controlled/tested.
        """
        super().__init__(parent)
        self.current_sn = current_sn
        self.new_sn: str = ''
        self.setWindowFlags(Qt.WindowType.Dialog)
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
        self.setWindowTitle('Enter Serial Number')

        # Apply styling
        apply_stylesheet(self, theme='dark_lightgreen.xml', invert_secondary=True)
        self.setStyleSheet(
            self.styleSheet() + """QLineEdit, QTextEdit {color: lightgreen;}"""
        )

        # Create the entry box to type in the new serial number
        self.serial_number_entry = QLineEdit(placeholderText=self.current_sn)

        # Create the OK and Cancel buttons
        self.ok_btn = QPushButton('OK')
        self.cancel_btn = QPushButton('Cancel')

        # Connect the buttons to their handlers
        self.ok_btn.clicked.connect(self.ok_btn_handler)
        self.cancel_btn.clicked.connect(self.cancel_btn_handler)

        # Configure the layout
        main_layout = QGridLayout()
        main_layout.addWidget(self.serial_number_entry, 0, 0, 1, 2)
        main_layout.addWidget(self.ok_btn, 1, 0)
        main_layout.addWidget(self.cancel_btn, 1, 1)

        self.setLayout(main_layout)

    def ok_btn_handler(self) -> None:
        self.serial_number: str = self.serial_number_entry.text()
        self.SN_changed.emit(self.serial_number)
        self.window_closed.emit()
        self.close()

    def cancel_btn_handler(self) -> None:
        self.window_closed.emit()
        self.close()
