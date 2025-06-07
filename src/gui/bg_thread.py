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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('QThread + QTimer QLabel Update')

        self.label = QLabel('Waiting...')
        layout = QVBoxLayout()
        layout.addWidget(self.label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.worker_thread = QThread()
        self.worker = Worker()
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.start)
        self.worker.updated.connect(self.update_label)

        self.worker_thread.start()

        # Prepare to handle safe shutdown
        self.worker.stopped.connect(self.on_worker_stopped)
        self._ready_to_quit = False

    def update_label(self, text) -> None:
        self.label.setText(text)

    def closeEvent(self, event) -> None:
        if self._ready_to_quit:
            event.accept()
        else:
            self._ready_to_quit = False
            self.worker.stop_requested.emit()
            event.ignore()  # Wait for cleanup

    def on_worker_stopped(self) -> None:
        self.worker_thread.quit()
        self.worker_thread.wait()
        self._ready_to_quit = True
        self.close()  # Now close safely


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
