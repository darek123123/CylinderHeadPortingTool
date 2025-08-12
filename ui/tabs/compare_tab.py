from __future__ import annotations

from typing import Any, Dict, List
from PySide6 import QtWidgets

from ..widgets.plots import Plot
from ..widgets.tables import SimpleTableModel
from ..state import UIState
from ... import api
from ... import io
from ..theme import COLORS


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
        self.metric = QtWidgets.QComboBox(); self.metric.addItems(["Flow","SAE CD","Eff SAE CD","v_mean","v_eff","Energy","Energy Density","Observed/area"]) 
        self.show_pct = QtWidgets.QCheckBox("Pokaż %Δ")
        self.btn = QtWidgets.QPushButton("Porównaj")
        self.btn_load_a_si = QtWidgets.QPushButton("Wczytaj TXT A (SI)")
        self.btn_load_a_us = QtWidgets.QPushButton("Wczytaj TXT A (US)")
        self.btn_load_b_si = QtWidgets.QPushButton("Wczytaj TXT B (SI)")
        self.btn_load_b_us = QtWidgets.QPushButton("Wczytaj TXT B (US)")
        self.btn.clicked.connect(self.on_compare)
        self.show_pct.toggled.connect(self.on_compare)
        self.metric.currentIndexChanged.connect(self.on_compare)
        self.btn_load_a_si.clicked.connect(lambda: self.on_import("A","SI"))
        self.btn_load_a_us.clicked.connect(lambda: self.on_import("A","US"))
        self.btn_load_b_si.clicked.connect(lambda: self.on_import("B","SI"))
        self.btn_load_b_us.clicked.connect(lambda: self.on_import("B","US"))
        for w in [self.units, self.mode, self.metric, self.show_pct, self.btn, self.btn_load_a_si, self.btn_load_a_us, self.btn_load_b_si, self.btn_load_b_us]:
            top.addWidget(w)
        self.plot = Plot()
        self.table = QtWidgets.QTableView()
        # export button
        export_row = QtWidgets.QHBoxLayout(); self.btn_export = QtWidgets.QPushButton("Zapisz wykres PNG"); export_row.addWidget(self.btn_export)
        self.btn_export.clicked.connect(self.on_export)
        # toast
        self._toast = QtWidgets.QLabel(""); self._toast.setStyleSheet("color:white; background: rgba(0,0,0,160); padding: 6px; border-radius: 4px;"); self._toast.setVisible(False)
        layout.addWidget(self._toast)
        layout.addLayout(top)
        layout.addWidget(self.plot.widget)
        layout.addLayout(export_row)
        layout.addWidget(self.table)
        # local state
        self._A_rows = []
        self._B_rows = []

    def on_compare(self):
        # Use imported rows if present, else fall back to a small synthetic pair
        units = self.units.currentText(); mode = self.mode.currentText()
        A_points = self._A_rows or [
            {"lift_mm": 2.0, "q_m3min": 0.2, "a_mean_mm2": 300.0, "d_valve_mm": 44.0},
            {"lift_mm": 6.0, "q_m3min": 0.5, "a_mean_mm2": 300.0, "d_valve_mm": 44.0},
            {"lift_mm": 10.0, "q_m3min": 0.8, "a_mean_mm2": 300.0, "d_valve_mm": 44.0}]
        B_points = self._B_rows or [
            {"lift_mm": 2.0, "q_m3min": 0.22, "a_mean_mm2": 300.0, "d_valve_mm": 44.0},
            {"lift_mm": 6.0, "q_m3min": 0.52, "a_mean_mm2": 300.0, "d_valve_mm": 44.0},
            {"lift_mm": 10.0, "q_m3min": 0.82, "a_mean_mm2": 300.0, "d_valve_mm": 44.0}]
        data = api.compare_tests(units, mode, A_points, B_points)
        x = data["xB"]
        # Pick metric
        metric_key = self.metric.currentText()
        series_map = {
            "Flow": ("flowA","flowB","flowPct"),
            "SAE CD": ("cdA","cdB","cdPct"),
            "Eff SAE CD": ("effcdA","effcdB","effcdPct"),
            "v_mean": ("velA","velB","velPct"),
            "v_eff": ("effvelA","effvelB","effvelPct"),
            "Energy": ("energyA","energyB","energyPct"),
            "Energy Density": ("energyDensityA","energyDensityB","energyDensityPct"),
            "Observed/area": ("areaA","areaB","areaPct"),
        }
        a_key, b_key, p_key = series_map.get(metric_key, ("flowA","flowB","flowPct"))
        yA, yB = data[a_key], data[b_key]
        self.plot.clear()
        self.plot.add_series("A", x, yA, "intake")
        self.plot.add_series("B", x, yB, "exhaust")
        pct_vals = data[p_key]
        # Optionally draw %Δ series by sign (two series: pos/neg)
        if self.show_pct.isChecked():
            x_pos = [xx for xx, vv in zip(x, pct_vals) if vv is not None and vv > 0]
            y_pos = [vv for vv in pct_vals if vv is not None and vv > 0]
            x_neg = [xx for xx, vv in zip(x, pct_vals) if vv is not None and vv < 0]
            y_neg = [vv for vv in pct_vals if vv is not None and vv < 0]
            if x_pos:
                self.plot.add_series("%Δ +", x_pos, y_pos, "percent_pos", symbol="o")
            if x_neg:
                self.plot.add_series("%Δ -", x_neg, y_neg, "percent_neg", symbol="o")
        headers = ["A","B","%Δ"] if self.show_pct.isChecked() else ["A","B"]
        rows = [[a, b, (pct if (self.show_pct.isChecked() and pct is not None) else None)] for a, b, pct in zip(yA, yB, pct_vals)]
        model = SimpleTableModel(headers, rows, percent_cols=([2] if self.show_pct.isChecked() else []))
        self.table.setModel(model)

    def on_import(self, which: str, units: str):
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

    def on_export(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Zapisz wykres", "compare.png", "PNG Files (*.png)")
        if path:
            self.plot.export_png(path)

    def _show_toast(self, text: str):
        self._toast.setText(text)
        self._toast.setVisible(True)
        QtWidgets.QTimer.singleShot(2200, lambda: self._toast.setVisible(False))
