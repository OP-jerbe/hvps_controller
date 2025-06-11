from PySide6.QtCore import QObject, QTimer, Signal


class Worker(QObject):
    updated = Signal()
    stop_requested = Signal()
    stopped = Signal()

    def __init__(self) -> None:
        super().__init__()
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
        self.stopped.emit()

    def on_timeout(self) -> None:
        self.updated.emit()
