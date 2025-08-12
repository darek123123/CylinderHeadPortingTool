from __future__ import annotations

from typing import Any, Dict, List
from PySide6 import QtWidgets

from ..widgets.inputs import LabeledSpin
from ..widgets.plots import Plot
from ..widgets.tables import SimpleTableModel
from ..state import UIState
from ... import api


class FlowTestTab(QtWidgets.QWidget):
    def __init__(self, state: UIState, parent=None):
        super().__init__(parent)
        self.state = state
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        top = QtWidgets.QHBoxLayout()
        self.units = QtWidgets.QComboBox(); self.units.addItems(["SI","US"])
        self.max_lift = LabeledSpin("Max lift", "mm")
        self.cr = LabeledSpin("CR")
        self.d_in = LabeledSpin("Valve In", "mm")
        self.d_ex = LabeledSpin("Valve Ex", "mm")
        self.calc = QtWidgets.QPushButton("Przelicz")
        self.calc.clicked.connect(self.on_compute)
        for w in [self.units, self.max_lift, self.cr, self.d_in, self.d_ex, self.calc]:
            top.addWidget(w)

        self.table = QtWidgets.QTableView()
        self.plot = Plot()

        layout.addLayout(top)
        layout.addWidget(self.table)
        layout.addWidget(self.plot.widget)

    def on_compute(self):
        units = self.units.currentText()
        header = {
            "max_lift_mm": float(self.max_lift.value()),
            "cr": float(self.cr.value()),
            "d_valve_in_mm": float(self.d_in.value()),
            "d_valve_ex_mm": float(self.d_ex.value()),
            "in_width_mm": 1.0, "in_height_mm": 1.0, "in_r_top_mm": 0.0, "in_r_bot_mm": 0.0,
            "ex_width_mm": 1.0, "ex_height_mm": 1.0, "ex_r_top_mm": 0.0, "ex_r_bot_mm": 0.0,
            "rows_in": [], "rows_ex": [],
        }
        rows = [
            {"lift_mm": 2.0, "q_in_m3min": 0.2, "q_ex_m3min": 0.18, "dp_inH2O": 28.0},
            {"lift_mm": 6.0, "q_in_m3min": 0.5, "q_ex_m3min": 0.45, "dp_inH2O": 28.0},
            {"lift_mm": 10.0, "q_in_m3min": 0.8, "q_ex_m3min": 0.7, "dp_inH2O": 28.0}
        ]
        data = api.flowtest_compute(units, header, rows)
        hdr = data["header"]
        table_rows = [
            [r["lift_mm"], r["q_in_m3min"], r["q_ex_m3min"]] for r in rows
        ]
        model = SimpleTableModel(["Lift", "Q_in", "Q_ex"], table_rows)
        self.table.setModel(model)
        xs = [r["lift_mm"] for r in rows]
        ys_in = [r["q_in_m3min"] for r in rows]
        ys_ex = [r["q_ex_m3min"] for r in rows]
        self.plot.clear()
        self.plot.add_series("In", xs, ys_in, "intake")
        self.plot.add_series("Ex", xs, ys_ex, "exhaust")
