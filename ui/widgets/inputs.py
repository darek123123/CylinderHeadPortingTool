from __future__ import annotations

from typing import Optional
from PySide6 import QtWidgets


class LabeledSpin(QtWidgets.QWidget):
    def __init__(self, label: str, suffix: str = "", parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        self.lbl = QtWidgets.QLabel(label)
        self.spin = QtWidgets.QDoubleSpinBox()
        self.spin.setDecimals(4)
        self.spin.setRange(-1e9, 1e9)
        if suffix:
            self.spin.setSuffix(f" {suffix}")
        layout.addWidget(self.lbl)
        layout.addWidget(self.spin)

    def value(self) -> float:
        return float(self.spin.value())

    def setValue(self, v: float):
        self.spin.setValue(v)
