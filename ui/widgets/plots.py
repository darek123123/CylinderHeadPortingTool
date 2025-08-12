from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from PySide6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
from ..theme import COLORS


class Plot(QtCore.QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.widget = pg.PlotWidget(background=COLORS["bg"])
        self.widget.showGrid(x=True, y=True, alpha=0.3)
        self.widget.getPlotItem().getAxis('left').setPen(COLORS["neutral"])
        self.widget.getPlotItem().getAxis('bottom').setPen(COLORS["neutral"])
        self.legend = self.widget.addLegend()
        pg.setConfigOptions(antialias=True)
        self._series = {}
        self._cross_v = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(COLORS["grid"]))
        self._cross_h = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen(COLORS["grid"]))
        self.widget.addItem(self._cross_v)
        self.widget.addItem(self._cross_h)
        self._xy_label = QtWidgets.QLabel("")
        proxy = QtWidgets.QGraphicsProxyWidget()
        proxy.setWidget(self._xy_label)
        self.widget.addItem(proxy)
        self._xy_label.setStyleSheet("color: #B0BEC5; background: transparent;")
        # Mouse move for crosshair
        self.widget.scene().sigMouseMoved.connect(self._on_mouse_moved)

    def add_series(self, name: str, x: List[float], y: List[float], color_token: str, line_width: int = 2, symbol: Optional[str] = None):
        pen = pg.mkPen(COLORS.get(color_token, COLORS["neutral"]), width=line_width)
        item = self.widget.plot(x, y, name=name, pen=pen, symbol=symbol)
        self._series[name] = item
        self._attach_legend_interaction()
        return item

    def update_series(self, name: str, x: List[float], y: List[float]):
        if name in self._series:
            self._series[name].setData(x, y)

    def clear(self):
        self.widget.clear()
        self._series.clear()
        self.legend = self.widget.addLegend()
        self.widget.addItem(self._cross_v)
        self.widget.addItem(self._cross_h)

    def export_png(self, path: str):
        exporter = ImageExporter(self.widget.plotItem)
        exporter.export(path)

    def add_threshold_line(self, y: float, color_token: str, label: str = ""):
        pen = pg.mkPen(COLORS.get(color_token, COLORS["neutral"]))
        line = pg.InfiniteLine(angle=0, movable=False, pen=pen, label=label, labelOpts={"position":0.95, "color":COLORS.get(color_token, "#fff")})
        self.widget.addItem(line)
        return line

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
        mousePoint = vb.mapSceneToView(pos)
        x = mousePoint.x(); y = mousePoint.y()
        self._cross_v.setPos(x)
        self._cross_h.setPos(y)
        self._xy_label.setText(f"x={x:.3f}, y={y:.3f}")

    def _attach_legend_interaction(self):
        # Install mouse press/double press events on legend items
        for sample, label in getattr(self.legend, 'items', []):
            item_name = label.text
            if not hasattr(label, 'mousePressEvent'):
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
