import sys
from socket import SocketType
from typing import NoReturn, Optional

from PySide6.QtWidgets import QApplication

from helpers.constants import IP, PORT, TIMEOUT
from helpers.helpers import open_socket
from src.gui.main_window import MainWindow

"""
TODO:
1) Write the User Guide
"""


def run_app(sock: Optional[SocketType]) -> NoReturn:
    """
    Sets the version of application build, creates the app and main window, then
    executes the application event loop. `app.exec() == 0` when the event loop
    stops. `sys.exit(0)` terminates the application.

    """
    version = '1.0.0'
    app = QApplication([])
    window = MainWindow(version=version, sock=sock)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    """
    Try to open a connection to the HVPS then run the app.
    """
    sock = open_socket(IP, PORT, TIMEOUT)
    run_app(sock)
