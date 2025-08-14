from __future__ import annotations

from typing import List, Optional
from PySide6 import QtCore, QtGui
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
from ..theme import COLORS


class Plot(QtCore.QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Core plot widget
        self.widget = pg.PlotWidget(background=COLORS["bg"])
        self.widget.showGrid(x=True, y=True, alpha=0.3)
        self.widget.getPlotItem().getAxis('left').setPen(COLORS["neutral"])
        self.widget.getPlotItem().getAxis('bottom').setPen(COLORS["neutral"])
        self.legend = self.widget.addLegend()
        pg.setConfigOptions(antialias=True)

        # State
        self._series: dict[str, pg.PlotDataItem] = {}
        self._x_unit = ""
        self._y_unit = ""
        self._x_label = ""
        self._y_label = ""

        # Crosshair
        self._cross_v = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(COLORS["grid"]))
        self._cross_h = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen(COLORS["grid"]))
        self._cross_v.setZValue(10)
        self._cross_h.setZValue(10)
        self.widget.addItem(self._cross_v, ignoreBounds=True)
        self.widget.addItem(self._cross_h, ignoreBounds=True)

        # XY label overlay
        self._xy_text = pg.TextItem("", color=COLORS["neutral"])  # type: ignore[arg-type]
        self._xy_text.setZValue(1000)
        self._xy_text.setAnchor((0, 1))
        self.widget.addItem(self._xy_text, ignoreBounds=True)

        # Mouse move for crosshair (rate-limited)
        self._mouse_proxy = pg.SignalProxy(self.widget.scene().sigMouseMoved, rateLimit=60, slot=self._on_mouse_moved_evt)

        # Extra markers storage
        self._markers: List[pg.InfiniteLine] = []

    def add_series(self, name: str, x: List[float], y: List[float], color_token: str, line_width: int = 2, symbol: Optional[str] = None):
        pen = pg.mkPen(COLORS.get(color_token, COLORS["neutral"]), width=line_width)
        item = self.widget.plot(x, y, name=name, pen=pen, symbol=symbol)
        self._series[name] = item
        self._attach_legend_interaction()
        # One-shot autorange
        try:
            self.widget.enableAutoRange('xy', True)
        except Exception:
            pass
        return item

    def update_series(self, name: str, x: List[float], y: List[float]):
        if name in self._series:
            self._series[name].setData(x, y)

    def clear(self):
        self.widget.clear()
        self._series.clear()
        self.legend = self.widget.addLegend()
        # Re-add overlays with ignoreBounds
        self._cross_v.setZValue(10)
        self._cross_h.setZValue(10)
        self.widget.addItem(self._cross_v, ignoreBounds=True)
        self.widget.addItem(self._cross_h, ignoreBounds=True)
        self.widget.addItem(self._xy_text, ignoreBounds=True)
        self._markers.clear()
        # Re-apply axis labels
        if self._x_label or self._x_unit:
            self.widget.setLabel('bottom', self._x_label)
        if self._y_label or self._y_unit:
            self.widget.setLabel('left', self._y_label)

    def export_png(self, path: str):
        exporter = ImageExporter(self.widget.plotItem)
        exporter.export(path)

    def add_threshold_line(self, y: float, color_token: str, label: str = ""):
        pen = pg.mkPen(COLORS.get(color_token, COLORS["neutral"]))
        line = pg.InfiniteLine(angle=0, movable=False, pen=pen, label=label, labelOpts={"position": 0.95, "color": COLORS.get(color_token, "#fff")})
        self.widget.addItem(line)
        return line

    def add_vertical_marker(self, x: float, color_token: str = "neutral", label: Optional[str] = None):
        pen = pg.mkPen(COLORS.get(color_token, COLORS["neutral"]))
        line = pg.InfiniteLine(pos=x, angle=90, movable=False, pen=pen)
        self.widget.addItem(line)
        if label:
            txt = pg.TextItem(label, color=COLORS.get(color_token, COLORS["neutral"]))  # type: ignore[arg-type]
            txt.setAnchor((0, 1))
            self.widget.addItem(txt, ignoreBounds=True)
            vb = self.widget.getViewBox()
            if vb is not None:
                try:
                    y_range = vb.viewRange()[1]
                    txt.setPos(x, y_range[1])
                except Exception:
                    pass
        self._markers.append(line)
        return line

    def set_units(self, x_unit: str = "", y_unit: str = ""):
        self._x_unit = x_unit
        self._y_unit = y_unit
        if self._x_label:
            self.widget.setLabel('bottom', self._x_label)
        if self._y_label:
            self.widget.setLabel('left', self._y_label)

    def set_axis_labels(self, x_label: str = "", y_label: str = ""):
        self._x_label = x_label
        self._y_label = y_label
        if x_label:
            self.widget.setLabel('bottom', x_label)
        if y_label:
            self.widget.setLabel('left', y_label)

    def toggle_series(self, name: str):
        item = self._series.get(name)
        if not item:
            return
        item.setVisible(not item.isVisible())

    def solo_series(self, name: str):
        for n, it in self._series.items():
            it.setVisible(n == name)

    # Internal helpers
    def _on_mouse_moved(self, pos):
        vb = self.widget.plotItem.vb
        if vb is None or pos is None:
            return
        mousePoint = vb.mapSceneToView(pos)
        x = mousePoint.x()
        y = mousePoint.y()
        self._cross_v.setPos(x)
        self._cross_h.setPos(y)
        xu = f" {self._x_unit}" if self._x_unit else ""
        yu = f" {self._y_unit}" if self._y_unit else ""
        self._xy_text.setText(f"x={x:.3f}{xu}, y={y:.3f}{yu}")
        try:
            (x0, x1), (y0, y1) = vb.viewRange()
            self._xy_text.setPos(x0, y1)
        except Exception:
            self._xy_text.setPos(x, y)

    def _on_mouse_moved_evt(self, args):
        pos = args[0] if isinstance(args, (list, tuple)) and args else args
        self._on_mouse_moved(pos)

    def _attach_legend_interaction(self):
        for sample, label in getattr(self.legend, 'items', []):
            item_name = getattr(label, 'text', None)
            if not item_name or not hasattr(label, 'mousePressEvent'):
                continue
            def _make_press(name: str):
                def _press(ev):
                    if ev.button() == QtCore.Qt.LeftButton:
                        self.toggle_series(name)
                return _press
            def _make_double(name: str):
                def _dbl(ev):
                    if ev.button() == QtCore.Qt.LeftButton:
                        self.solo_series(name)
                return _dbl
            label.mousePressEvent = _make_press(item_name)
            label.mouseDoubleClickEvent = _make_double(item_name)
