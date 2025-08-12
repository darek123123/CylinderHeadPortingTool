from __future__ import annotations

from typing import Any, Dict, List
from PySide6 import QtWidgets

from ..widgets.plots import Plot
from ..widgets.tables import SimpleTableModel
from ..state import UIState
from ... import api


class CompareTab(QtWidgets.QWidget):
    def __init__(self, state: UIState, parent=None):
        super().__init__(parent)
        self.state = state
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        top = QtWidgets.QHBoxLayout()
        self.units = QtWidgets.QComboBox(); self.units.addItems(["SI","US"])
        self.mode = QtWidgets.QComboBox(); self.mode.addItems(["lift","ld"]) 
        self.show_pct = QtWidgets.QCheckBox("%Δ")
        self.btn = QtWidgets.QPushButton("Porównaj")
        self.btn.clicked.connect(self.on_compare)
        for w in [self.units, self.mode, self.show_pct, self.btn]:
            top.addWidget(w)
        self.plot = Plot()
        self.table = QtWidgets.QTableView()
        layout.addLayout(top)
        layout.addWidget(self.plot.widget)
        layout.addWidget(self.table)

    def on_compare(self):
        # Minimal synthetic data for smoke; in real app, load from state
        units = self.units.currentText()
        mode = self.mode.currentText()
        A_points = [
            {"lift_mm": 2.0, "q_m3min": 0.2, "a_mean_mm2": 300.0, "d_valve_mm": 44.0},
            {"lift_mm": 6.0, "q_m3min": 0.5, "a_mean_mm2": 300.0, "d_valve_mm": 44.0},
            {"lift_mm": 10.0, "q_m3min": 0.8, "a_mean_mm2": 300.0, "d_valve_mm": 44.0}
        ]
        B_points = [
            {"lift_mm": 2.0, "q_m3min": 0.22, "a_mean_mm2": 300.0, "d_valve_mm": 44.0},
            {"lift_mm": 6.0, "q_m3min": 0.52, "a_mean_mm2": 300.0, "d_valve_mm": 44.0},
            {"lift_mm": 10.0, "q_m3min": 0.82, "a_mean_mm2": 300.0, "d_valve_mm": 44.0}
        ]
        data = api.compare_tests(units, mode, A_points, B_points)
        x = data["xB"]
        yA, yB = data["flowA"], data["flowB"]
        self.plot.clear()
        self.plot.add_series("A", x, yA, "intake")
        self.plot.add_series("B", x, yB, "exhaust")
        table_rows = [[a, b, (None if b==0 else (a-b)/b*100.0)] for a, b in zip(yA, yB)]
        self.table.setModel(SimpleTableModel(["A","B","%Δ"], table_rows))
