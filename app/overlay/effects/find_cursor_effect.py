"""尋找游標輔助（十字準線／脈動圓圈）的繪製邏輯。"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen

from app.config import FindCursorConfig

_HIGHLIGHT_COLOR = "#FF3B30"


def paint(
  painter: QPainter,
  cursor_local_pos: QPointF,
  widget_size: QSize,
  elapsed_s: float,
  config: FindCursorConfig,
) -> None:
  color = QColor(_HIGHLIGHT_COLOR)
  if config.effect_style in ("crosshair", "both"):
    _paint_crosshair(painter, cursor_local_pos, widget_size, color)
  if config.effect_style in ("pulse_circle", "both"):
    _paint_pulse_circle(painter, cursor_local_pos, elapsed_s, color)


def _paint_crosshair(painter: QPainter, cursor_local_pos: QPointF, widget_size: QSize, color: QColor) -> None:
  painter.setPen(QPen(color, 3))
  painter.drawLine(0, int(cursor_local_pos.y()), widget_size.width(), int(cursor_local_pos.y()))
  painter.drawLine(int(cursor_local_pos.x()), 0, int(cursor_local_pos.x()), widget_size.height())


def _paint_pulse_circle(painter: QPainter, cursor_local_pos: QPointF, elapsed_s: float, color: QColor) -> None:
  radius = 40 + 30 * abs(math.sin(elapsed_s * 4))
  pulse_color = QColor(color)
  pulse_color.setAlphaF(0.7)
  painter.setPen(QPen(pulse_color, 4))
  painter.setBrush(Qt.BrushStyle.NoBrush)
  painter.drawEllipse(cursor_local_pos, radius, radius)
