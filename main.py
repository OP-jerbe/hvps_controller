import sys
from typing import NoReturn

from PySide6.QtWidgets import QApplication

from src.gui.main_window import MainWindow


def run_app() -> NoReturn:
    """
    Sets the version of application build,
    creates the app and main window,
    then executes the application event loop.
    app.exec() == 0 when the event loop stops.
    sys.exit(0) terminates the application.
    """
    version = '1.0.0'
    app = QApplication([])
    window = MainWindow(version=version)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    run_app()
