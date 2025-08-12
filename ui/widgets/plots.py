from __future__ import annotations

from typing import Dict, List, Optional
from PySide6 import QtCore
import pyqtgraph as pg
from ..theme import COLORS


class Plot(QtCore.QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.widget = pg.PlotWidget(background=COLORS["bg"])
        self.widget.showGrid(x=True, y=True, alpha=0.3)
        self.widget.getPlotItem().getAxis('left').setPen(COLORS["neutral"])
        self.widget.getPlotItem().getAxis('bottom').setPen(COLORS["neutral"])
        self.widget.addLegend()
        pg.setConfigOptions(antialias=True)
        self._series: Dict[str, pg.PlotDataItem] = {}
        self._cross = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(COLORS["grid"]))
        self.widget.addItem(self._cross)

    def add_series(self, name: str, x: List[float], y: List[float], color_token: str, line_width: int = 2, symbol: Optional[str] = None):
        pen = pg.mkPen(COLORS.get(color_token, COLORS["neutral"]), width=line_width)
        item = self.widget.plot(x, y, name=name, pen=pen, symbol=symbol)
        self._series[name] = item
        return item

    def update_series(self, name: str, x: List[float], y: List[float]):
        if name in self._series:
            self._series[name].setData(x, y)

    def clear(self):
        self.widget.clear()
        self._series.clear()

    def export_png(self, path: str):
        exporter = pg.exporters.ImageExporter(self.widget.plotItem)
        exporter.export(path)
