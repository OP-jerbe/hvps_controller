import sys
from socket import SocketType
from typing import NoReturn, Optional

from PySide6.QtWidgets import QApplication

from helpers.constants import IP, PORT, TIMEOUT
from helpers.helpers import open_socket
from src.gui.main_window import MainWindow

"""
TODO:
1) Add a `BACK` button to the test window that allows the user to go back to the previous channel test

2) Add a `RESTART` button to the test window that allows the user to restart the current test
(or figure out a way add the measurements and readbacks to their proper spots in the readbacks and measurements lists)
######## I think I figured this out. Need to test out the HVPSTestWindow.
######## Make sure QLineEdits are disabled when the gui is loaded.
######## Make sure when the Test HV button is pressed, the correct QLineEdit is enabled and the other buttons are disabled and focus moves to QLineEdit
######## Make sure when enter is pressed, the QLineEdit is disabled, the buttons are enabled and the focus goes to the next button.

3) Get the actual pictures showing voltmeter setup for each test into the assets folder.

4) Write the User Guide
"""


def run_app(sock: Optional[SocketType]) -> NoReturn:
    """
    Sets the version of application build,
    creates the app and main window,
    then executes the application event loop.
    app.exec() == 0 when the event loop stops.
    sys.exit(0) terminates the application.
    """
    version = '1.0.0'
    app = QApplication([])
    window = MainWindow(version=version, sock=sock)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    # try and connect to the HVPS then run the app.
    sock = open_socket(IP, PORT, TIMEOUT)
    run_app(sock)
