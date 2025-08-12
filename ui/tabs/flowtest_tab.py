from __future__ import annotations

from typing import Any, Dict, List
from PySide6 import QtWidgets

from ..widgets.inputs import LabeledSpin
from ..widgets.plots import Plot
from ..widgets.tables import SimpleTableModel
from ..state import UIState
from ... import api
from ... import io


class FlowTestTab(QtWidgets.QWidget):
    def __init__(self, state: UIState, parent=None):
        super().__init__(parent)
        self.state = state
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Top controls
        top = QtWidgets.QHBoxLayout()
        self.units = QtWidgets.QComboBox(); self.units.addItems(["SI", "US"])
        self.max_lift = LabeledSpin("Max lift", "mm")
        self.cr = LabeledSpin("CR")
        self.d_in = LabeledSpin("Valve In", "mm")
        self.d_ex = LabeledSpin("Valve Ex", "mm")
        self.calc = QtWidgets.QPushButton("Przelicz"); self.calc.clicked.connect(self.on_compute)
        self.btn_import_si = QtWidgets.QPushButton("Import TXT (SI)"); self.btn_import_si.clicked.connect(self.on_import_si)
        self.btn_import_us = QtWidgets.QPushButton("Import TXT (US)"); self.btn_import_us.clicked.connect(self.on_import_us)
        for w in [self.units, self.max_lift, self.cr, self.d_in, self.d_ex, self.calc, self.btn_import_si, self.btn_import_us]:
            top.addWidget(w)

        # Table and plot
        self.table = QtWidgets.QTableView()
        self.plot = Plot()

        # Controls below plot: axis and series toggles, export
        controls = QtWidgets.QHBoxLayout()
        self.axis = QtWidgets.QComboBox(); self.axis.addItems(["lift", "ld"])  # x-axis
        self.chk_in = QtWidgets.QCheckBox("Intake")
        self.chk_ex = QtWidgets.QCheckBox("Exhaust")
        self.chk_in.setChecked(True); self.chk_ex.setChecked(True)
        self.btn_export_png = QtWidgets.QPushButton("Export PNG"); self.btn_export_png.clicked.connect(self.on_export_png)
        for w in [QtWidgets.QLabel("Axis:"), self.axis, self.chk_in, self.chk_ex, self.btn_export_png]:
            controls.addWidget(w)

        # Assemble layout
        layout.addLayout(top)
        layout.addWidget(self.table)
        layout.addWidget(self.plot.widget)
        layout.addLayout(controls)

        # cache of last compute
        self._last_series = {}
        self._last_x = {}
        self._last_rows = []
        self._last_units = "SI"

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
        self._render(units, header, rows)

    def on_import_si(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open SI report", "", "Text Files (*.txt)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            parsed = io.parse_iop_report_si(text)
            header = parsed["flow_header"]
            rows = parsed["flow_rows"]
            self.units.setCurrentText("SI")
            self._render("SI", header, rows)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Import error", str(e))

    def on_import_us(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open US report", "", "Text Files (*.txt)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            parsed = io.parse_iop_report_us(text)
            header = parsed["flow_header"]
            rows = parsed["flow_rows"]
            self.units.setCurrentText("US")
            self._render("US", header, rows)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Import error", str(e))

    def on_export_png(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export plot", "flow.png", "PNG Files (*.png)")
        if path:
            self.plot.export_png(path)

    def _render(self, units: str, header: Dict[str, Any], rows: List[Dict[str, Any]]):
        data = api.flowtest_compute(units, header, rows)
        self._last_series = data.get("series", {})
        self._last_x = data.get("x", {})
        self._last_rows = rows
        self._last_units = units
        # Table basic view
        table_rows = [[r.get("lift_mm"), r.get("q_in_m3min"), r.get("q_ex_m3min")] for r in rows]
        model = SimpleTableModel(["Lift", "Q_in", "Q_ex"], table_rows)
        self.table.setModel(model)
        # Plot according to axis and series toggle
        self._update_plot_from_series()
        # React to changes
        self.axis.currentIndexChanged.connect(self._update_plot_from_series)
        self.chk_in.toggled.connect(self._update_plot_from_series)
        self.chk_ex.toggled.connect(self._update_plot_from_series)

    def _update_plot_from_series(self):
        if not self._last_series:
            return
        self.plot.clear()
        if self.axis.currentText() == "lift":
            x_int = x_ex = self._last_x.get("lift_mm", [])
        else:
            x_int = self._last_x.get("ld_int", [])
            x_ex = self._last_x.get("ld_ex", [])
        if self.chk_in.isChecked():
            self.plot.add_series("Intake", x_int, self._last_series.get("flow_int", []), "intake")
        if self.chk_ex.isChecked():
            self.plot.add_series("Exhaust", x_ex, self._last_series.get("flow_ex", []), "exhaust")
