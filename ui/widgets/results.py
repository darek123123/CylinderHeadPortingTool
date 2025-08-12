from __future__ import annotations

from PySide6 import QtWidgets
from ..theme import COLORS, THRESHOLDS


class MetricCard(QtWidgets.QFrame):
    def __init__(self, title: str, unit: str = "", parent=None):
        super().__init__(parent)
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        layout = QtWidgets.QVBoxLayout(self)
        self.title = QtWidgets.QLabel(title)
        self.value = QtWidgets.QLabel("—")
        self.unit = QtWidgets.QLabel(unit)
        self.badge = QtWidgets.QLabel("")
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.unit)
        layout.addWidget(self.badge)
        self.setObjectName("MetricCard")

    def set_value(self, v: float):
        self.value.setText(f"{v:.2f}")

    def set_badge(self, level: str):
        txt = {"ok": "OK", "warn": "WARN", "crit": "CRIT"}.get(level, "")
        self.badge.setText(txt)
