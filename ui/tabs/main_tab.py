from __future__ import annotations

from typing import Dict, Any
from PySide6 import QtWidgets

from ..widgets.inputs import LabeledSpin
from ..widgets.results import MetricCard
from ..widgets.plots import Plot
from ..state import UIState
from ... import api


class MainTab(QtWidgets.QWidget):
    def __init__(self, state: UIState, parent=None):
        super().__init__(parent)
        self.state = state
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QHBoxLayout(self)

        left = QtWidgets.QVBoxLayout()
        right = QtWidgets.QVBoxLayout()

        self.units = QtWidgets.QComboBox()
        self.units.addItems(["SI", "US"])  # explicit

        self.bore = LabeledSpin("Bore", "mm")
        self.stroke = LabeledSpin("Stroke", "mm")
        self.n_cyl = LabeledSpin("Cyl")
        self.ve = LabeledSpin("VE")
        self.mach = LabeledSpin("Mach")
        self.cr = LabeledSpin("CR")
        self.n_ports_eff = LabeledSpin("Ports eff")
        self.calc = QtWidgets.QPushButton("Przelicz")
        self.calc.clicked.connect(self.on_calc)

        form = QtWidgets.QFormLayout()
        form.addRow("Units", self.units)
        for w in [self.bore, self.stroke, self.n_cyl, self.ve, self.mach, self.cr, self.n_ports_eff]:
            form.addRow(w)
        left.addLayout(form)
        left.addWidget(self.calc)

        # Results
        self.card_rpm = MetricCard("Peak RPM", "rpm")
        self.card_shift = MetricCard("Shift RPM", "rpm")
        self.card_mps = MetricCard("Mean Piston Speed", "m/min")
        right.addWidget(self.card_rpm)
        right.addWidget(self.card_shift)
        right.addWidget(self.card_mps)

        self.plot = Plot()
        right.addWidget(self.plot.widget)

        layout.addLayout(left)
        layout.addLayout(right)

    def on_calc(self):
        units = self.units.currentText()
        inputs: Dict[str, Any] = {
            "mach": float(self.mach.value()),
            "mean_port_area_mm2": 1800.0,
            "bore_mm": float(self.bore.value()),
            "stroke_mm": float(self.stroke.value()),
            "n_cyl": int(self.n_cyl.value()),
            "ve": float(self.ve.value()),
            "n_ports_eff": float(self.n_ports_eff.value()),
            "cr": float(self.cr.value()),
        }
        data = api.compute_main_screen(units, inputs)
        self.card_rpm.set_value(data.get("peak_rpm", 0.0))
        self.card_shift.set_value(data.get("shift_rpm", 0.0))
        self.card_mps.set_value(data.get("mean_piston_speed_m_min", 0.0))
        # simple plot
        xs = [0, 1]
        ys = [data.get("peak_rpm", 0.0), data.get("shift_rpm", 0.0)]
        self.plot.clear()
        self.plot.add_series("RPM", xs, ys, "percent_pos")
