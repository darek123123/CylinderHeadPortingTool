from __future__ import annotations

from PySide6 import QtCore


class Worker(QtCore.QRunnable):
    success = QtCore.Signal(dict)
    error = QtCore.Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    @QtCore.Slot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            QtCore.QMetaObject.invokeMethod(self, "emit_success", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(dict, result))
        except Exception as e:
            QtCore.QMetaObject.invokeMethod(self, "emit_error", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, str(e)))

    @QtCore.Slot(dict)
    def emit_success(self, payload: dict):
        self.success.emit(payload)

    @QtCore.Slot(str)
    def emit_error(self, msg: str):
        self.error.emit(msg)


class Debounce(QtCore.QObject):
    triggered = QtCore.Signal()
    def __init__(self, ms: int = 200):
        super().__init__()
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(ms)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.triggered)

    def pulse(self):
        self.timer.start()
