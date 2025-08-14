from __future__ import annotations

import sys
from PySide6 import QtCore, QtWidgets

from .app import App


def _install_qt_warning_filter() -> None:
    """Silence a noisy, non-critical Qt warning flooding the console.

    We only filter the specific message observed at runtime to avoid hiding other issues.
    """

    def _handler(mode, context, message: str):  # type: ignore[no-untyped-def]
        if "QGraphicsItem::itemTransform: null pointer passed" in message:
            return  # drop this one message
        # forward everything else to stderr
        sys.stderr.write(message + "\n")

    # Install early so it applies during app startup
    try:
        QtCore.qInstallMessageHandler(_handler)
    except Exception:
        # Best-effort: if install fails for any reason, continue without filtering
        pass


def main():
    _install_qt_warning_filter()
    app = QtWidgets.QApplication(sys.argv)
    win = App()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
