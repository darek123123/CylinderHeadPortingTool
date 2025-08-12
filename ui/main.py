from __future__ import annotations

import os
import sys
from PySide6 import QtWidgets

from .app import App


def main():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # safe default for tests
    app = QtWidgets.QApplication(sys.argv)
    win = App()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
