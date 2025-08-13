from __future__ import annotations

from typing import Any, List, Optional
from PySide6 import QtCore, QtGui, QtWidgets
from ..theme import COLORS, THRESHOLDS


class SimpleTableModel(QtCore.QAbstractTableModel):
    def __init__(self, headers: List[str], rows: List[List[Any]], *,
                 vel_cols: Optional[List[int]] = None,
                 eff_vel_cols: Optional[List[int]] = None,
                 mach_cols: Optional[List[int]] = None,
                 percent_cols: Optional[List[int]] = None):
        super().__init__()
        self.headers = headers
        self.rows = rows
        self.vel_cols = set(vel_cols or [])
        self.eff_vel_cols = set(eff_vel_cols or [])
        self.mach_cols = set(mach_cols or [])
        self.percent_cols = set(percent_cols or [])

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.rows)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.headers)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        val = self.rows[index.row()][index.column()]
        if role == QtCore.Qt.DisplayRole:
            return "—" if val is None else f"{val:.3f}" if isinstance(val, float) else str(val)
        if role == QtCore.Qt.BackgroundRole and isinstance(val, float):
            col = index.column()
            # Velocity mean thresholds
            if col in self.vel_cols:
                if val >= THRESHOLDS["vel_mean_crit_ms"]:
                    return QtGui.QColor(COLORS["crit"]).lighter(180)
                if val >= THRESHOLDS["vel_mean_warn_ms"]:
                    return QtGui.QColor(COLORS["warn"]).lighter(180)
            # Effective velocity thresholds
            if col in self.eff_vel_cols:
                if val >= THRESHOLDS["vel_eff_crit_ms"]:
                    return QtGui.QColor(COLORS["crit"]).lighter(180)
                if val >= THRESHOLDS["vel_eff_warn_ms"]:
                    return QtGui.QColor(COLORS["warn"]).lighter(180)
            # Mach thresholds
            if col in self.mach_cols:
                if val >= THRESHOLDS["mach_intake_crit"]:
                    return QtGui.QColor(COLORS["crit"]).lighter(180)
                if val >= THRESHOLDS["mach_intake_warn"]:
                    return QtGui.QColor(COLORS["warn"]).lighter(180)
            # Percent delta thresholds (color by sign, threshold by magnitude)
            if col in self.percent_cols:
                mag = abs(val)
                # Prefer new fractional thresholds if values seem fractional (-1..+1), else fall back to legacy % points
                if mag <= 1.0:
                    if mag >= THRESHOLDS.get("pct_crit", 0.10):
                        base = QtGui.QColor(COLORS["percent_pos"] if val >= 0 else COLORS["percent_neg"])
                        return base.lighter(170)
                    if mag >= THRESHOLDS.get("pct_warn", 0.05):
                        base = QtGui.QColor(COLORS["percent_pos"] if val >= 0 else COLORS["percent_neg"])
                        return base.lighter(200)
                else:
                    if mag >= THRESHOLDS["percent_crit"]:
                        base = QtGui.QColor(COLORS["percent_pos"] if val >= 0 else COLORS["percent_neg"])
                        return base.lighter(170)
                    if mag >= THRESHOLDS["percent_warn"]:
                        base = QtGui.QColor(COLORS["percent_pos"] if val >= 0 else COLORS["percent_neg"])
                        return base.lighter(200)
        return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self.headers[section]
        return None

    # Export to CSV
    def export_csv(self, path: str):
        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self.headers)
            for r in self.rows:
                writer.writerow(["" if v is None else v for v in r])
