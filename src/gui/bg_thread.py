import sys

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget


class Worker(QObject):
    updated = Signal(str)
    stop_requested = Signal()
    stopped = Signal()  # NEW: emitted when timer is fully stopped

    def __init__(self) -> None:
        super().__init__()
        self.counter = 0
        self.timer = None
        self.stop_requested.connect(self.stop)

    def start(self) -> None:
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.on_timeout)
        self.timer.start()

    def stop(self) -> None:
        if self.timer and self.timer.isActive():
            self.timer.stop()
        self.stopped.emit()  # Notify that cleanup is done

    def on_timeout(self) -> None:
        self.counter += 1
        self.updated.emit(f'Seconds passed: {self.counter}')
