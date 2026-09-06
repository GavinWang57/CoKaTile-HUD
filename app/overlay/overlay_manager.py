"""管理每個螢幕的覆蓋層視窗、共享渲染狀態與動畫更新。"""
from __future__ import annotations

import math
import time

from PySide6.QtCore import QObject, QPointF, QRect, QTimer
from PySide6.QtGui import QGuiApplication, QScreen

from app.config import AppConfig
from app.overlay.overlay_window import OverlayWindow
from app.overlay.render_state import ClickRipple, OverlayRenderState

_ANIMATION_INTERVAL_MS = 16
_SPOTLIGHT_SNAP_THRESHOLD_PX = 0.5


def _compute_smoothed_position(
  current: QPointF, target: QPointF, smoothing: float, max_lag: float
) -> tuple[QPointF, bool]:
  """讓顯示位置平滑追向目標，但與目標的距離永遠不超過 max_lag。回傳 (下一步位置, 是否仍需要繼續動畫)。"""
  diff = target - current
  distance = math.hypot(diff.x(), diff.y())
  if distance <= _SPOTLIGHT_SNAP_THRESHOLD_PX:
    return target, False

  new_pos = current + diff * smoothing
  new_diff = target - new_pos
  new_distance = math.hypot(new_diff.x(), new_diff.y())
  if new_distance > max_lag > 0:
    scale = max_lag / new_distance
    new_pos = QPointF(target.x() - new_diff.x() * scale, target.y() - new_diff.y() * scale)
  return new_pos, True


class OverlayManager(QObject):
  def __init__(self, config: AppConfig, parent: QObject | None = None):
    super().__init__(parent)
    self._config = config
    self._state = OverlayRenderState()
    self._windows: dict[QScreen, OverlayWindow] = {}
    self._animation_timer = QTimer(self)
    self._animation_timer.setInterval(_ANIMATION_INTERVAL_MS)
    self._animation_timer.timeout.connect(self._on_animation_tick)

    app = QGuiApplication.instance()
    app.screenAdded.connect(self._on_screen_added)
    app.screenRemoved.connect(self._on_screen_removed)
    for screen in app.screens():
      self._create_window_for_screen(screen)

  @property
  def cursor_global_pos(self) -> QPointF | None:
    return self._state.cursor_global_pos

  def shutdown(self) -> None:
    self._animation_timer.stop()
    for window in self._windows.values():
      window.close()
    self._windows.clear()

  def set_config(self, config: AppConfig) -> None:
    self._config = config
    for window in self._windows.values():
      window.set_config(config)
    self._sync_visibility()
    self._update_all()

  def on_cursor_moved(self, x: int, y: int) -> None:
    self._state.cursor_global_pos = QPointF(x, y)
    if self._state.spotlight_display_pos is None:
      self._state.spotlight_display_pos = QPointF(x, y)
    if self._config.spotlight.enabled:
      self._ensure_animation_running()
    if self._state.find_cursor_active:
      self._update_all()

  def on_mouse_pressed(self, x: int, y: int, button: str) -> None:
    if not self._config.click_effect.enabled:
      return
    self._state.click_ripples.append(
      ClickRipple(global_pos=QPointF(x, y), button=button, start_time=time.monotonic())
    )
    self._ensure_animation_running()

  def trigger_find_cursor(self) -> None:
    if not self._config.find_cursor.enabled:
      return
    self._state.find_cursor_active = True
    self._state.find_cursor_start_time = time.monotonic()
    self._ensure_animation_running()

  def _create_window_for_screen(self, screen: QScreen) -> None:
    window = OverlayWindow(screen.geometry(), self._state, self._config)
    self._windows[screen] = window
    screen.geometryChanged.connect(lambda geo, s=screen: self._on_screen_geometry_changed(s, geo))
    if self._should_show_any_overlay():
      window.show()

  def _on_screen_added(self, screen: QScreen) -> None:
    self._create_window_for_screen(screen)

  def _on_screen_removed(self, screen: QScreen) -> None:
    window = self._windows.pop(screen, None)
    if window is not None:
      window.close()

  def _on_screen_geometry_changed(self, screen: QScreen, geometry: QRect) -> None:
    window = self._windows.get(screen)
    if window is not None:
      window.update_geometry(geometry)

  def _should_show_any_overlay(self) -> bool:
    return (
      self._config.spotlight.enabled
      or self._config.click_effect.enabled
      or self._config.find_cursor.enabled
    )

  def _sync_visibility(self) -> None:
    visible = self._should_show_any_overlay()
    for window in self._windows.values():
      window.setVisible(visible)

  def _update_all(self) -> None:
    for window in self._windows.values():
      window.update()

  def _ensure_animation_running(self) -> None:
    if not self._animation_timer.isActive():
      self._animation_timer.start()

  def _on_animation_tick(self) -> None:
    now = time.monotonic()

    spotlight_animating = self._advance_spotlight_position()

    self._state.click_ripples = [
      r
      for r in self._state.click_ripples
      if (now - r.start_time) * 1000.0 <= self._config.click_effect.duration_ms
    ]
    if self._state.find_cursor_active:
      elapsed_ms = (now - self._state.find_cursor_start_time) * 1000.0
      if elapsed_ms > self._config.find_cursor.effect_duration_ms:
        self._state.find_cursor_active = False

    self._update_all()

    if (
      not spotlight_animating
      and not self._state.click_ripples
      and not self._state.find_cursor_active
    ):
      self._animation_timer.stop()

  def _advance_spotlight_position(self) -> bool:
    if not self._config.spotlight.enabled:
      return False
    target = self._state.cursor_global_pos
    if target is None:
      return False
    current = self._state.spotlight_display_pos or target
    new_pos, animating = _compute_smoothed_position(
      current, target, self._config.spotlight.follow_smoothing, self._config.spotlight.radius
    )
    self._state.spotlight_display_pos = new_pos
    return animating
