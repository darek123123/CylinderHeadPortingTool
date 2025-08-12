from __future__ import annotations

from PySide6 import QtWidgets

from .state import UIState
from .tabs.main_tab import MainTab
from .tabs.flowtest_tab import FlowTestTab
from .tabs.compare_tab import CompareTab


class App(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CylinderHeadPortingTool")
        self.state = UIState()
        tabs = QtWidgets.QTabWidget()
        tabs.addTab(MainTab(self.state), "Main")
        tabs.addTab(FlowTestTab(self.state), "Flow Test")
        tabs.addTab(CompareTab(self.state), "Compare")
        self.setCentralWidget(tabs)
