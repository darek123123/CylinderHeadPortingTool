from __future__ import annotations

from typing import Any, Dict, List
from PySide6 import QtCore, QtWidgets

from ..widgets.plots import Plot
from ..widgets.tables import SimpleTableModel
from ..state import UIState
from ... import api
from ... import io


class CompareTab(QtWidgets.QWidget):
    def __init__(self, state: UIState, parent=None):
        super().__init__(parent)
        self.state = state
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        top = QtWidgets.QHBoxLayout()

        self.units = QtWidgets.QComboBox(); self.units.addItems(["SI", "US"])
        self.mode = QtWidgets.QComboBox(); self.mode.addItems(["lift", "ld"])  # x-axis mode
        self.side = QtWidgets.QComboBox(); self.side.addItems(["Intake", "Exhaust"])  # series side
        self.metric = QtWidgets.QComboBox(); self.metric.addItems([
            "Flow", "SAE CD", "Eff SAE CD", "Mean Vel", "Eff Vel", "Energy", "Energy Density", "Observed per area"
        ])
        self.show_pct = QtWidgets.QCheckBox("Pokaż %Δ")
        self.btn = QtWidgets.QPushButton("Porównaj")
        self.btn_load_a_si = QtWidgets.QPushButton("Wczytaj TXT A (SI)")
        self.btn_load_a_us = QtWidgets.QPushButton("Wczytaj TXT A (US)")
        self.btn_load_b_si = QtWidgets.QPushButton("Wczytaj TXT B (SI)")
        self.btn_load_b_us = QtWidgets.QPushButton("Wczytaj TXT B (US)")

        # wiring
        self.btn.clicked.connect(self.on_compare)
        self.show_pct.toggled.connect(self.on_compare)
        self.metric.currentIndexChanged.connect(self.on_compare)
        self.side.currentIndexChanged.connect(self.on_compare)
        self.units.currentIndexChanged.connect(self.on_compare)
        self.mode.currentIndexChanged.connect(self.on_compare)
        self.btn_load_a_si.clicked.connect(lambda: self.on_import("A", "SI"))
        self.btn_load_a_us.clicked.connect(lambda: self.on_import("A", "US"))
        self.btn_load_b_si.clicked.connect(lambda: self.on_import("B", "SI"))
        self.btn_load_b_us.clicked.connect(lambda: self.on_import("B", "US"))

        for w in [self.units, self.mode, self.side, self.metric, self.show_pct, self.btn,
                  self.btn_load_a_si, self.btn_load_a_us, self.btn_load_b_si, self.btn_load_b_us]:
            top.addWidget(w)

        self.plot = Plot()
        self.table = QtWidgets.QTableView()

        export_row = QtWidgets.QHBoxLayout()
        self.btn_export = QtWidgets.QPushButton("Zapisz wykres PNG"); export_row.addWidget(self.btn_export)
        self.btn_export_csv = QtWidgets.QPushButton("Eksport CSV"); export_row.addWidget(self.btn_export_csv)
        self.btn_export.clicked.connect(self.on_export)
        self.btn_export_csv.clicked.connect(self.on_export_csv)

        self._toast = QtWidgets.QLabel("")
        self._toast.setStyleSheet("color:white; background: rgba(0,0,0,160); padding: 6px; border-radius: 4px;")
        self._toast.setVisible(False)

        layout.addWidget(self._toast)
        layout.addLayout(top)
        layout.addWidget(self.plot.widget)
        layout.addLayout(export_row)
        layout.addWidget(self.table)

        # local state
        self._A_rows: List[Dict[str, Any]] = []
        self._B_rows: List[Dict[str, Any]] = []
        self._last_x: List[float] = []
        self._last_yA: List[float] = []
        self._last_yB: List[float] = []
        self._last_pct: List[float] = []

        # initial render
        self.on_compare()

    def on_compare(self) -> None:
        # Use imported rows if present, else fall back to a small synthetic pair
        units = self.units.currentText()
        mode = self.mode.currentText()
        A_points = self._A_rows or [
            {"lift_mm": 2.0, "q_m3min": 0.2, "a_mean_mm2": 300.0, "d_valve_mm": 44.0},
            {"lift_mm": 6.0, "q_m3min": 0.5, "a_mean_mm2": 300.0, "d_valve_mm": 44.0},
            {"lift_mm": 10.0, "q_m3min": 0.8, "a_mean_mm2": 300.0, "d_valve_mm": 44.0},
        ]
        B_points = self._B_rows or [
            {"lift_mm": 2.0, "q_m3min": 0.22, "a_mean_mm2": 300.0, "d_valve_mm": 44.0},
            {"lift_mm": 6.0, "q_m3min": 0.52, "a_mean_mm2": 300.0, "d_valve_mm": 44.0},
            {"lift_mm": 10.0, "q_m3min": 0.82, "a_mean_mm2": 300.0, "d_valve_mm": 44.0},
        ]
        data = api.compare_tests(units, mode, A_points, B_points)
        x_map = data.get("x", {})
        x = x_map.get("lift_mm", []) if mode == "lift" else x_map.get("ld_int", [])
        # Set axis units
        self.plot.set_units("mm" if mode == "lift" else "L/D", self._y_unit_for_metric())

        # Pick metric and side
        metric_key = self.metric.currentText()
        side = self.side.currentText()
        suffix = "_int" if side == "Intake" else "_ex"
        base_map = {
            "Flow": f"flow{suffix}",
            "SAE CD": f"sae_cd{suffix}",
            "Eff SAE CD": f"eff_cd{suffix}",
            "Mean Vel": f"v_mean{suffix}",
            "Eff Vel": f"v_eff{suffix}",
            "Energy": f"energy{suffix}",
            "Energy Density": f"energy_density{suffix}",
            "Observed per area": f"observed_per_area{suffix}",
        }
        base = base_map.get(metric_key, f"flow{suffix}")
        yA = data["A"].get(base, [])
        yB = data["B"].get(base, [])
        pct_vals = data.get("delta_pct", {}).get(base, [])

        # cache for CSV
        self._last_x, self._last_yA, self._last_yB, self._last_pct = x, yA, yB, pct_vals

        # Plot
        self.plot.clear()
        self.plot.add_series("A", x, yA, "intake")
        self.plot.add_series("B", x, yB, "exhaust")
        if self.show_pct.isChecked():
            x_pos = [xx for xx, vv in zip(x, pct_vals) if vv is not None and vv > 0]
            y_pos = [vv for vv in pct_vals if vv is not None and vv > 0]
            x_neg = [xx for xx, vv in zip(x, pct_vals) if vv is not None and vv < 0]
            y_neg = [vv for vv in pct_vals if vv is not None and vv < 0]
            if x_pos:
                self.plot.add_series("%Δ +", x_pos, y_pos, "percent_pos", symbol="o")
            if x_neg:
                self.plot.add_series("%Δ -", x_neg, y_neg, "percent_neg", symbol="o")

        # Table
        headers = ["X", "A", "B", "%Δ"] if self.show_pct.isChecked() else ["X", "A", "B"]
        rows = [[xx, a, b, (pct if (self.show_pct.isChecked() and pct is not None) else None)]
                for xx, a, b, pct in zip(x, yA, yB, pct_vals)]
        model = SimpleTableModel(headers, rows, percent_cols=([3] if self.show_pct.isChecked() else []))
        self.table.setModel(model)

    def on_import(self, which: str, units: str) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, f"Open {which} {units} report", "", "Text Files (*.txt)")
        if not path:
            return
        try:
            text = open(path, "r", encoding="utf-8").read()
            if units == "SI":
                parsed = io.parse_iop_report_si(text)
                rows = parsed["flow_rows"]
            else:
                parsed = io.parse_iop_report_us(text)
                rows = parsed["flow_rows"]
            if which == "A":
                self._A_rows = rows
            else:
                self._B_rows = rows
            self._show_toast(f"Załadowano {len(rows)} wierszy dla {which}")
            self.on_compare()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Import error", str(e))

    def on_export(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Zapisz wykres", "compare.png", "PNG Files (*.png)")
        if path:
            self.plot.export_png(path)

    def on_export_csv(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Eksport tabeli", "compare.csv", "CSV Files (*.csv)")
        if not path:
            return
        model = self.table.model()
        try:
            if hasattr(model, "export_csv"):
                model.export_csv(path)
            else:
                import csv
                with open(path, "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    headers = ["X", "A", "B", "%Δ"] if self.show_pct.isChecked() else ["X", "A", "B"]
                    w.writerow(headers)
                    for row in zip(self._last_x, self._last_yA, self._last_yB, self._last_pct):
                        x, a, b, pct = row
                        if self.show_pct.isChecked():
                            w.writerow([x, a, b, "" if pct is None else pct])
                        else:
                            w.writerow([x, a, b])
            self._show_toast("Zapisano CSV")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Export error", str(e))

    def _show_toast(self, text: str) -> None:
        self._toast.setText(text)
        self._toast.setVisible(True)
        QtCore.QTimer.singleShot(2200, lambda: self._toast.setVisible(False))

    def _y_unit_for_metric(self) -> str:
        m = self.metric.currentText() if hasattr(self, "metric") else "Flow"
        # Using SI-consistent units (backend compares in SI internally)
        if m == "Flow":
            return "m³/min"
        if m in ("SAE CD", "Eff SAE CD"):
            return "-"
        if m in ("Mean Vel", "Eff Vel"):
            return "m/s"
        if m == "Energy":
            return "J/m"
        if m == "Energy Density":
            return "J/m³"
        if m == "Observed per area":
            return "m³/min/mm²"
        return ""
