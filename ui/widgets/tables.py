from __future__ import annotations

from typing import Any, List
from PySide6 import QtCore, QtGui, QtWidgets
from ..theme import COLORS, THRESHOLDS


class SimpleTableModel(QtCore.QAbstractTableModel):
    def __init__(self, headers: List[str], rows: List[List[Any]]):
        super().__init__()
        self.headers = headers
        self.rows = rows

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
            # Example threshold coloring for percent
            if abs(val) >= THRESHOLDS["percent_crit"]:
                return QtGui.QColor(COLORS["crit"])  # background
            if abs(val) >= THRESHOLDS["percent_warn"]:
                return QtGui.QColor(COLORS["warn"])  # background
        return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self.headers[section]
        return None
