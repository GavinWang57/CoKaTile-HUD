"""單一螢幕的覆蓋層視窗，依序繪製聚光燈、點擊漣漪、尋找游標三種效果。"""
from __future__ import annotations

import time

from PySide6.QtCore import QPointF, QRect
from PySide6.QtGui import QPaintEvent, QPainter
from PySide6.QtWidgets import QWidget

from app.config import AppConfig
from app.overlay import base_overlay_widget
from app.overlay.effects import click_ripple_effect, find_cursor_effect, spotlight_effect
from app.overlay.render_state import OverlayRenderState


class OverlayWindow(QWidget):
  def __init__(
    self,
    screen_geometry: QRect,
    state: OverlayRenderState,
    config: AppConfig,
    parent: QWidget | None = None,
  ):
    super().__init__(parent)
    self._state = state
    self._config = config
    base_overlay_widget.apply_overlay_window_flags(self, click_through=True)
    self.setGeometry(screen_geometry)

  def set_config(self, config: AppConfig) -> None:
    self._config = config
    self.update()

  def update_geometry(self, screen_geometry: QRect) -> None:
    self.setGeometry(screen_geometry)

  def paintEvent(self, event: QPaintEvent) -> None:
    painter = QPainter(self)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    now = time.monotonic()

    if self._config.spotlight.enabled and self._state.spotlight_display_pos is not None:
      spotlight_effect.paint(
        painter, self._to_local(self._state.spotlight_display_pos), self.size(), self._config.spotlight
      )

    if self._config.click_effect.enabled and self._state.click_ripples:
      click_ripple_effect.paint(
        painter, self._state.click_ripples, self._to_local, now, self._config.click_effect
      )

    if self._state.find_cursor_active and self._state.cursor_global_pos is not None:
      elapsed = now - self._state.find_cursor_start_time
      find_cursor_effect.paint(
        painter,
        self._to_local(self._state.cursor_global_pos),
        self.size(),
        elapsed,
        self._config.find_cursor,
      )

  def _to_local(self, global_pos: QPointF) -> QPointF:
    top_left = self.geometry().topLeft()
    return QPointF(global_pos.x() - top_left.x(), global_pos.y() - top_left.y())
