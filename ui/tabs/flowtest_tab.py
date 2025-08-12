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
        self._signals_connected = False
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

        # Controls below plot: axis/metric selectors, series toggles, export
        controls = QtWidgets.QHBoxLayout()
        self.axis = QtWidgets.QComboBox(); self.axis.addItems(["lift", "ld"])  # x-axis
        self.metric = QtWidgets.QComboBox(); self.metric.addItems([
            "Flow", "SAE CD", "Eff SAE CD", "Mean Vel", "Eff Vel", "Energy", "Energy Density", "Observed per area"
        ])
        self.chk_in = QtWidgets.QCheckBox("Intake")
        self.chk_ex = QtWidgets.QCheckBox("Exhaust")
        self.chk_in.setChecked(True); self.chk_ex.setChecked(True)
        self.btn_export_png = QtWidgets.QPushButton("Export PNG"); self.btn_export_png.clicked.connect(self.on_export_png)
        for w in [QtWidgets.QLabel("Axis:"), self.axis, QtWidgets.QLabel("Metric:"), self.metric, self.chk_in, self.chk_ex, self.btn_export_png]:
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
        # Plot according to axis/metric and series toggle
        self._update_plot_from_series()
        # React to changes (connect once)
        if not self._signals_connected:
            self.axis.currentIndexChanged.connect(self._update_plot_from_series)
            self.metric.currentIndexChanged.connect(self._update_plot_from_series)
            self.chk_in.toggled.connect(self._update_plot_from_series)
            self.chk_ex.toggled.connect(self._update_plot_from_series)
            self._signals_connected = True

    def _update_plot_from_series(self):
        if not self._last_series:
            return
        self.plot.clear()
        # X axis and units
        if self.axis.currentText() == "lift":
            x_int = x_ex = self._last_x.get("lift_mm", [])
            self.plot.set_units("mm", self._y_unit_for_metric())
        else:
            x_int = self._last_x.get("ld_int", [])
            x_ex = self._last_x.get("ld_ex", [])
            self.plot.set_units("L/D", self._y_unit_for_metric())
        # Metric mapping to series keys
        metric_name = self.metric.currentText()
        key_map = {
            "Flow": ("flow_int", "flow_ex"),
            "SAE CD": ("sae_cd_int", "sae_cd_ex"),
            "Eff SAE CD": ("eff_cd_int", "eff_cd_ex"),
            "Mean Vel": ("v_mean_int", "v_mean_ex"),
            "Eff Vel": ("v_eff_int", "v_eff_ex"),
            "Energy": ("energy_int", "energy_ex"),
            "Energy Density": ("energy_density_int", "energy_density_ex"),
            "Observed per area": ("observed_per_area_int", "observed_per_area_ex"),
        }
        kin, kex = key_map.get(metric_name, ("flow_int", "flow_ex"))
        # Series
        if self.chk_in.isChecked():
            self.plot.add_series("Intake", x_int, self._last_series.get(kin, []), "intake")
        if self.chk_ex.isChecked():
            self.plot.add_series("Exhaust", x_ex, self._last_series.get(kex, []), "exhaust")
        # Threshold lines for velocities
        if metric_name in ("Mean Vel", "Eff Vel"):
            from ..theme import THRESHOLDS
            if metric_name == "Mean Vel":
                self.plot.add_threshold_line(THRESHOLDS["vel_mean_warn_ms"], "warn", "warn")
                self.plot.add_threshold_line(THRESHOLDS["vel_mean_crit_ms"], "crit", "crit")
            else:
                self.plot.add_threshold_line(THRESHOLDS["vel_eff_warn_ms"], "warn", "warn")
                self.plot.add_threshold_line(THRESHOLDS["vel_eff_crit_ms"], "crit", "crit")

    def _y_unit_for_metric(self) -> str:
        m = self.metric.currentText() if hasattr(self, "metric") else "Flow"
        if m == "Flow":
            return "m³/min" if self._last_units == "SI" else "CFM"
        if m in ("SAE CD", "Eff SAE CD"):
            return "-"
        if m in ("Mean Vel", "Eff Vel"):
            return "m/s" if self._last_units == "SI" else "ft/s"
        if m == "Energy":
            return "J/m" if self._last_units == "SI" else "ft·lbf"
        if m == "Energy Density":
            return "J/m³" if self._last_units == "SI" else "ft·lbf/in³"
        if m == "Observed per area":
            return "m³/min/mm²" if self._last_units == "SI" else "CFM/in²"
        return ""
