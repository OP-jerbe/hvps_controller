from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow

from helpers.helpers import get_root_dir


class MainWindow(QMainWindow):
    def __init__(self, version: str) -> None:
        super().__init__()
        self.version = version
        self.installEventFilter(self)
        self.create_gui()

    def create_gui(self) -> None:
        window_width = 550
        window_height = 500
        self.setFixedSize(window_width, window_height)

        root_dir: Path = get_root_dir()
        icon_path: str = str(root_dir / 'assets' / 'hvps_icon.ico')
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle(f'HVPSv3 Test Controller (v{self.version})')
