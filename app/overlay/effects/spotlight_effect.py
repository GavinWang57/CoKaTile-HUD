"""聚光燈／游標高亮圈的繪製邏輯。"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath

from app.config import SpotlightConfig


def paint(painter: QPainter, cursor_local_pos: QPointF, widget_size: QSize, config: SpotlightConfig) -> None:
  if config.mode == "spotlight":
    _paint_spotlight(painter, cursor_local_pos, widget_size, config)
  else:
    _paint_circle(painter, cursor_local_pos, config)


def _paint_circle(painter: QPainter, cursor_local_pos: QPointF, config: SpotlightConfig) -> None:
  color = QColor(config.color)
  color.setAlphaF(config.circle_opacity)
  painter.setPen(Qt.PenStyle.NoPen)
  painter.setBrush(color)
  painter.drawEllipse(cursor_local_pos, config.radius, config.radius)


def _paint_spotlight(
  painter: QPainter, cursor_local_pos: QPointF, widget_size: QSize, config: SpotlightConfig
) -> None:
  full = QPainterPath()
  full.addRect(0, 0, widget_size.width(), widget_size.height())
  hole = QPainterPath()
  hole.addEllipse(cursor_local_pos, config.radius, config.radius)
  dimmed_area = full.subtracted(hole)
  color = QColor(0, 0, 0)
  color.setAlphaF(config.dim_opacity)
  painter.fillPath(dimmed_area, color)
