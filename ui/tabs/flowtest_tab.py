from __future__ import annotations

from typing import Any, Dict, List
from PySide6 import QtWidgets, QtCore

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

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)

        # Top: left inputs + right plot
        top_widget = QtWidgets.QWidget()
        top_layout = QtWidgets.QHBoxLayout(top_widget)

        # Left inputs panel
        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        inputs_form = QtWidgets.QFormLayout()
        self.units = QtWidgets.QComboBox()
        self.units.addItems(["SI", "US"])
        self.max_lift = LabeledSpin("Max lift", "mm")
        self.cr = LabeledSpin("CR")
        self.d_in = LabeledSpin("Valve In", "mm")
        self.d_ex = LabeledSpin("Valve Ex", "mm")
        inputs_form.addRow("Units", self.units)
        for w in [self.max_lift, self.cr, self.d_in, self.d_ex]:
            inputs_form.addRow(w)
        left_layout.addLayout(inputs_form)

        # Buttons
        btn_row = QtWidgets.QHBoxLayout()
        self.calc = QtWidgets.QPushButton("Przelicz")
        self.calc.clicked.connect(self.on_compute)
        self.btn_export_hdr = QtWidgets.QPushButton("Export header metrics")
        self.btn_export_hdr.clicked.connect(self.on_export_header_metrics)
        self.btn_sample = QtWidgets.QPushButton("Próbka")
        self.btn_sample.clicked.connect(self.on_sample_menu)
        self.btn_import_si = QtWidgets.QPushButton("Import TXT (SI)")
        self.btn_import_si.clicked.connect(self.on_import_si)
        self.btn_import_us = QtWidgets.QPushButton("Import TXT (US)")
        self.btn_import_us.clicked.connect(self.on_import_us)
        for w in [self.calc, self.btn_export_hdr, self.btn_sample, self.btn_import_si, self.btn_import_us]:
            btn_row.addWidget(w)
        left_layout.addLayout(btn_row)

        # Collapsible Geometry group
        self.grp_geom = QtWidgets.QGroupBox("Geometry")
        self.grp_geom.setCheckable(True)
        self.grp_geom.setChecked(False)
        geom_form = QtWidgets.QFormLayout()
        self.in_w = LabeledSpin("In width", "mm")
        self.in_h = LabeledSpin("In height", "mm")
        self.in_rtop = LabeledSpin("In r top", "mm")
        self.in_rbot = LabeledSpin("In r bot", "mm")
        self.ex_w = LabeledSpin("Ex width", "mm")
        self.ex_h = LabeledSpin("Ex height", "mm")
        self.ex_rtop = LabeledSpin("Ex r top", "mm")
        self.ex_rbot = LabeledSpin("Ex r bot", "mm")
        self.seat_ai = LabeledSpin("Seat angle In", "deg")
        self.seat_ae = LabeledSpin("Seat angle Ex", "deg")
        self.seat_wi = LabeledSpin("Seat width In", "mm")
        self.seat_we = LabeledSpin("Seat width Ex", "mm")
        for w in [self.in_w, self.in_h, self.in_rtop, self.in_rbot, self.ex_w, self.ex_h, self.ex_rtop, self.ex_rbot, self.seat_ai, self.seat_ae, self.seat_wi, self.seat_we]:
            geom_form.addRow(w)
        self.grp_geom.setLayout(geom_form)
        left_layout.addWidget(self.grp_geom)

        # Right: plot and controls
        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        self.plot = Plot()
        right_layout.addWidget(self.plot.widget)
        controls = QtWidgets.QHBoxLayout()
        self.axis = QtWidgets.QComboBox()
        self.axis.addItems(["lift", "ld"])  # x-axis
        self.metric = QtWidgets.QComboBox()
        self.metric.addItems([
            "Flow", "SAE CD", "Eff SAE CD", "Mean Vel", "Eff Vel", "Energy", "Energy Density", "Observed per area"
        ])
        self.chk_in = QtWidgets.QCheckBox("Intake")
        self.chk_in.setChecked(True)
        self.chk_ex = QtWidgets.QCheckBox("Exhaust")
        self.chk_ex.setChecked(True)
        self.btn_export_png = QtWidgets.QPushButton("Export PNG")
        self.btn_export_png.clicked.connect(self.on_export_png)
        for w in [QtWidgets.QLabel("Axis:"), self.axis, QtWidgets.QLabel("Metric:"), self.metric, self.chk_in, self.chk_ex, self.btn_export_png]:
            controls.addWidget(w)
        right_layout.addLayout(controls)

        # Assemble top
        top_layout.addWidget(left_panel, 0)
        top_layout.addWidget(right_panel, 1)

        # Bottom: tabs with Rows and Header tables
        bottom_tabs = QtWidgets.QTabWidget()
        self.table_rows = QtWidgets.QTableView()
        self.table_header = QtWidgets.QTableView()
        # Back-compat for tests expecting a single 'table' attribute
        self.table = self.table_rows
        bottom_tabs.addTab(self.table_rows, "Rows")
        bottom_tabs.addTab(self.table_header, "Header")

        splitter_top_bottom = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter_top_bottom.addWidget(top_widget)
        splitter_top_bottom.addWidget(bottom_tabs)
        splitter_top_bottom.setStretchFactor(0, 3)
        splitter_top_bottom.setStretchFactor(1, 1)

        root.addWidget(splitter_top_bottom)

        # cache
        self._last_series = {}
        self._last_x = {}
        self._last_rows = []
        self._last_units = "SI"
        self._last_units_map = {}

    def on_sample_menu(self) -> None:
        menu = QtWidgets.QMenu(self)
        act = menu.addAction('E7TE (SI, 28")')
        act.triggered.connect(self._apply_e7te_si)
        act2 = menu.addAction('SI – szybka próbka (28")')
        act2.triggered.connect(self._apply_quick_si)
        menu.exec(self.mapToGlobal(self.rect().bottomLeft()))

    def _apply_e7te_si(self) -> None:
        # Build header/rows for E7TE at 28" H2O (all SI). No math here; backend does everything.
        header: Dict[str, Any] = {
            # Units hint (API gets units separately)
            "units": "SI",
            "cr": 9.0,
            "max_lift_mm": 17.78,
            "test_pressure_inH2O": 28.0,
            # Port window geometry (rect with two radii)
            "in_width_mm": 30.861,
            "in_height_mm": 55.118,
            "in_r_top_mm": 10.16,
            "in_r_bot_mm": 10.16,
            "ex_width_mm": 34.798,
            "ex_height_mm": 34.036,
            "ex_r_top_mm": 10.16,
            "ex_r_bot_mm": 10.16,
            # Port window areas as reported (extra keys)
            "port_area_in_mm2": 1612.255,
            "port_area_ex_mm2": 1095.776,
            # Valves
            "d_valve_in_mm": 51.308,
            "d_valve_ex_mm": 40.64,
            # Alternate names to mirror DV reports (ignored by backend)
            "valve_in_mm": 51.308,
            "valve_ex_mm": 40.64,
            # Stems
            "d_stem_in_mm": 8.687,
            "d_stem_ex_mm": 8.687,
            # Throats (diameters); areas will be derived inside backend
            "d_throat_in_mm": 39.37,
            "d_throat_ex_mm": 32.512,
            # Throat areas from DV (extra keys for traceability)
            "throat_area_in_mm2": 1219.35,
            "throat_area_ex_mm2": 830.19,
            # Seats
            "seat_angle_in_deg": 52.0,
            "seat_angle_ex_deg": 42.0,
            "seat_width_in_mm": 1.143,
            "seat_width_ex_mm": 1.651,
            # Optional descriptors
            "port_length_centerline_mm": 136.398,  # generic centerline
            "port_centerline_len_in_mm": 136.398,
            "port_centerline_len_ex_mm": 73.152,
            # metrics helpers (rows will be populated below)
            "rows_in": [],
            "rows_ex": [],
            "ex_pipe_used": False,
        }
        rows: List[Dict[str, Any]] = [
            {"lift_mm": 1.27,  "q_in_m3min": 1.0137, "q_ex_m3min": 0.6966, "dp_inH2O": 28.0},
            {"lift_mm": 2.54,  "q_in_m3min": 2.0671, "q_ex_m3min": 1.4725, "dp_inH2O": 28.0},
            {"lift_mm": 3.81,  "q_in_m3min": 3.1149, "q_ex_m3min": 2.1804, "dp_inH2O": 28.0},
            {"lift_mm": 5.08,  "q_in_m3min": 4.1059, "q_ex_m3min": 3.0865, "dp_inH2O": 28.0},
            {"lift_mm": 6.35,  "q_in_m3min": 4.7855, "q_ex_m3min": 3.8681, "dp_inH2O": 28.0},
            {"lift_mm": 7.62,  "q_in_m3min": 5.4793, "q_ex_m3min": 4.1824, "dp_inH2O": 28.0},
            {"lift_mm": 8.89,  "q_in_m3min": 5.9890, "q_ex_m3min": 4.5590, "dp_inH2O": 28.0},
            {"lift_mm": 10.16, "q_in_m3min": 6.5129, "q_ex_m3min": 5.0687, "dp_inH2O": 28.0},
            {"lift_mm": 12.70, "q_in_m3min": 7.2888, "q_ex_m3min": 5.3207, "dp_inH2O": 28.0},
            {"lift_mm": 15.24, "q_in_m3min": 7.5889, "q_ex_m3min": 5.3406, "dp_inH2O": 28.0},
            {"lift_mm": 17.78, "q_in_m3min": 7.8438, "q_ex_m3min": 5.6237, "dp_inH2O": 28.0},
            {"lift_mm": 20.32, "q_in_m3min": 7.9854, "q_ex_m3min": 5.8616, "dp_inH2O": 28.0},
            {"lift_mm": 22.86, "q_in_m3min": 8.0420, "q_ex_m3min": 6.0881, "dp_inH2O": 28.0},
            {"lift_mm": 25.40, "q_in_m3min": 8.0703, "q_ex_m3min": 6.2863, "dp_inH2O": 28.0},
        ]
        # For header metrics (averages/totals/ratios), supply rows_in/ex with corrected flows
        header["rows_in"] = [{"m3min_corr": r["q_in_m3min"], "dp_inH2O": r["dp_inH2O"]} for r in rows]
        header["rows_ex"] = [{"m3min_corr": r["q_ex_m3min"], "dp_inH2O": r["dp_inH2O"]} for r in rows]
        self.units.setCurrentText("SI")
        self._render("SI", header, rows)

    def _apply_quick_si(self) -> None:
        # 10 rows: lift 1.5–12 mm step 1 mm, dp 28, minimal header
        header: Dict[str, Any] = {
            "units": "SI",
            "cr": 10.0,
            "max_lift_mm": 12.0,
            "d_valve_in_mm": 45.0,
            "d_valve_ex_mm": 38.0,
            "in_width_mm": 30.0, "in_height_mm": 50.0, "in_r_top_mm": 8.0, "in_r_bot_mm": 8.0,
            "ex_width_mm": 28.0, "ex_height_mm": 40.0, "ex_r_top_mm": 6.0, "ex_r_bot_mm": 6.0,
            "rows_in": [], "rows_ex": [],
        }
        rows: List[Dict[str, Any]] = []
        lift = 1.5
        while lift <= 12.0 + 1e-9:
            rows.append({"lift_mm": round(lift, 3), "q_in_m3min": 0.1 * lift, "q_ex_m3min": 0.09 * lift, "dp_inH2O": 28.0})
            lift += 1.0
        self.units.setCurrentText("SI")
        self._render("SI", header, rows)

    def on_compute(self) -> None:
        units = self.units.currentText()
        # Basic validation for required fields (>0)
        required_fields = [
            ("Max lift", float(self.max_lift.value())),
            ("CR", float(self.cr.value())),
            ("Valve In", float(self.d_in.value())),
            ("Valve Ex", float(self.d_ex.value())),
            ("In width", float(self.in_w.value())),
            ("In height", float(self.in_h.value())),
            ("Ex width", float(self.ex_w.value())),
            ("Ex height", float(self.ex_h.value())),
        ]
        bad = [name for name, v in required_fields if v <= 0]
        if bad:
            QtWidgets.QMessageBox.critical(self, "Validation error", f"Fields must be > 0: {', '.join(bad)}")
            return
        header = {
            "max_lift_mm": float(self.max_lift.value()),
            "cr": float(self.cr.value()),
            "d_valve_in_mm": float(self.d_in.value()),
            "d_valve_ex_mm": float(self.d_ex.value()),
            # Geometry (do not override user input)
            "in_width_mm": float(self.in_w.value()),
            "in_height_mm": float(self.in_h.value()),
            "in_r_top_mm": float(self.in_rtop.value()),
            "in_r_bot_mm": float(self.in_rbot.value()),
            "ex_width_mm": float(self.ex_w.value()),
            "ex_height_mm": float(self.ex_h.value()),
            "ex_r_top_mm": float(self.ex_rtop.value()),
            "ex_r_bot_mm": float(self.ex_rbot.value()),
            # Optional seats (include if provided)
            **({"seat_angle_in_deg": float(self.seat_ai.value())} if self.seat_ai.value() > 0 else {}),
            **({"seat_angle_ex_deg": float(self.seat_ae.value())} if self.seat_ae.value() > 0 else {}),
            **({"seat_width_in_mm": float(self.seat_wi.value())} if self.seat_wi.value() > 0 else {}),
            **({"seat_width_ex_mm": float(self.seat_we.value())} if self.seat_we.value() > 0 else {}),
            # Header metrics helpers
            "rows_in": [],
            "rows_ex": [],
        }
        # Minimal synthetic rows with 28" to drive computations
        rows: List[Dict[str, Any]] = [
            {"lift_mm": 0.25 * float(self.max_lift.value()), "q_in_m3min": 0.1, "q_ex_m3min": 0.08, "dp_inH2O": 28.0},
            {"lift_mm": 0.50 * float(self.max_lift.value()), "q_in_m3min": 0.2, "q_ex_m3min": 0.16, "dp_inH2O": 28.0},
            {"lift_mm": 1.00 * float(self.max_lift.value()), "q_in_m3min": 0.3, "q_ex_m3min": 0.24, "dp_inH2O": 28.0},
        ]
        try:
            self._render(units, header, rows)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Compute error", str(e))

    def on_export_header_metrics(self) -> None:
        try:
            if not self._last_units or not hasattr(self, "_last_series"):
                QtWidgets.QMessageBox.information(self, "Export", "No data to export. Compute first.")
                return
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export header metrics", "header_metrics.csv", "CSV Files (*.csv)")
            if not path:
                return
            # Use cached last header from last render
            # we stored header metrics in the header table model
            hdr_items = []
            model = self.table_header.model()
            if isinstance(model, SimpleTableModel):
                for row in model.rows:
                    if len(row) >= 2:
                        hdr_items.append((str(row[0]), row[1]))
            import csv
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Key", "Value"])
                for k, v in hdr_items:
                    w.writerow([k, v])
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Export error", str(e))

    def on_import_si(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open SI report", "", "Text Files (*.txt)")
        if not path:
            return
        try:
            text = open(path, "r", encoding="utf-8").read()
            parsed = io.parse_iop_report_si(text)
            header = parsed["flow_header"]
            rows = parsed["flow_rows"]
            self.units.setCurrentText("SI")
            self._render("SI", header, rows)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Import error", str(e))

    def on_import_us(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open US report", "", "Text Files (*.txt)")
        if not path:
            return
        try:
            text = open(path, "r", encoding="utf-8").read()
            parsed = io.parse_iop_report_us(text)
            header = parsed["flow_header"]
            rows = parsed["flow_rows"]
            self.units.setCurrentText("US")
            self._render("US", header, rows)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Import error", str(e))

    def on_export_png(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export plot", "flow.png", "PNG Files (*.png)")
        if path:
            self.plot.export_png(path)

    def _render(self, units: str, header: Dict[str, Any], rows: List[Dict[str, Any]]) -> None:
        data = api.flowtest_compute(units, header, rows)
        self._last_series = data.get("series", {})
        self._last_x = data.get("x", {})
        self._last_rows = rows
        self._last_units = units
        self._last_units_map = data.get("units", {}) or {}
        # Tables: prefer API-provided normalized table with headers incl. units
        table = data.get("table") or {}
        headers = table.get("headers") or ["Lift [mm]", "Q_in", "Q_ex"]
        table_rows_data = table.get("rows") or rows
        # if table rows are dicts, map basic columns; else assume already list
        if table_rows_data and isinstance(table_rows_data[0], dict):
            table_rows = [[r.get("lift_mm"), r.get("q_in_m3min"), r.get("q_ex_m3min")] for r in table_rows_data]
        else:
            table_rows = table_rows_data
        model_rows = SimpleTableModel(headers, table_rows)
        self.table_rows.setModel(model_rows)
        # Header metrics table (flat key/value for visibility)
        hdr = data.get("header", {}) or {}
        hdr_items = [[k, hdr[k]] for k in hdr.keys()]
        model_hdr = SimpleTableModel(["Key", "Value"], hdr_items)
        self.table_header.setModel(model_hdr)
        # Plot
        self._update_plot_from_series()
        if not self._signals_connected:
            self.axis.currentIndexChanged.connect(self._update_plot_from_series)
            self.metric.currentIndexChanged.connect(self._update_plot_from_series)
            self.chk_in.toggled.connect(self._update_plot_from_series)
            self.chk_ex.toggled.connect(self._update_plot_from_series)
            self._signals_connected = True

    def _update_plot_from_series(self) -> None:
        if not self._last_series:
            return
        self.plot.clear()
        # X axis and units
        if self.axis.currentText() == "lift":
            x_int = x_ex = self._last_x.get("lift_mm", [])
            self.plot.set_units("mm", self._y_unit_for_metric())
            self.plot.set_axis_labels("Lift [mm]", f"{self._y_unit_for_metric()}")
        else:
            x_int = self._last_x.get("ld_int", [])
            x_ex = self._last_x.get("ld_ex", [])
            self.plot.set_units("L/D", self._y_unit_for_metric())
            self.plot.set_axis_labels("L/D [-]", f"{self._y_unit_for_metric()}")
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
        units_map = self._last_units_map or {}
        if m == "Flow":
            return units_map.get("flow", "")
        if m in ("SAE CD", "Eff SAE CD"):
            return units_map.get("cd", "-")
        if m in ("Mean Vel", "Eff Vel"):
            return units_map.get("vel", "")
        if m == "Energy":
            return units_map.get("energy", "")
        if m == "Energy Density":
            return units_map.get("energy_density", "")
        if m == "Observed per area":
            return units_map.get("observed_per_area", "")
        return ""
