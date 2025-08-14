from __future__ import annotations

import sys
from PySide6 import QtWidgets

from .app import App


def main():
    app = QtWidgets.QApplication(sys.argv)
    win = App()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
