from __future__ import annotations

from PySide6 import QtWidgets, QtGui
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

    def set_value(self, v: float, unit: str = "", kind: str | None = None):
        """Set value and compute badge based on THRESHOLDS.
        kind examples: 'mach_intake', 'vel_mean_ms', 'vel_eff_ms'.
        """
        self.value.setText(f"{v:.2f}")
        if unit:
            self.unit.setText(unit)
        level = "ok"
        if kind:
            # Map kind to thresholds
            if kind == "mach_intake":
                w = THRESHOLDS.get("mach_intake_warn")
                c = THRESHOLDS.get("mach_intake_crit")
            elif kind == "vel_mean_ms":
                w = THRESHOLDS.get("vel_mean_warn_ms")
                c = THRESHOLDS.get("vel_mean_crit_ms")
            elif kind == "vel_eff_ms":
                w = THRESHOLDS.get("vel_eff_warn_ms")
                c = THRESHOLDS.get("vel_eff_crit_ms")
            else:
                w = c = None
            if w is not None and c is not None:
                if v >= c:
                    level = "crit"
                elif v >= w:
                    level = "warn"
        self._apply_badge(level)

    def _apply_badge(self, level: str):
        txt = {"ok": "OK", "warn": "WARN", "crit": "CRIT"}.get(level, "")
        self.badge.setText(txt)
        color = COLORS.get(level, COLORS["neutral"])
        pal = self.badge.palette()
        pal.setColor(QtGui.QPalette.WindowText, QtGui.QColor(color))
        self.badge.setPalette(pal)
