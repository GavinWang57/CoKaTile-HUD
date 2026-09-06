"""顯示目前按下的鍵盤按鍵與滑鼠按鈕，支援按住/連點/放開三種狀態的視覺呈現。"""
from __future__ import annotations

import time

from PySide6.QtCore import QPointF, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPaintEvent, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.config import KeyHudConfig
from app.hud.key_badge import KeyBadge
from app.overlay import base_overlay_widget

_ANIMATION_INTERVAL_MS = 33
_BADGE_SPACING = 8
_BADGE_PADDING = 12
_MARGIN = 24
_FOLLOW_CURSOR_OFFSET = 24
_COMBO_WINDOW_S = 0.4  # 放開後多快再次按下會被視為「連點」而非新的一筆


class KeyHudWindow(QWidget):
  def __init__(self, screen_geometry: QRect, config: KeyHudConfig, parent: QWidget | None = None):
    super().__init__(parent)
    self._config = config
    self._badges: list[KeyBadge] = []
    self._cursor_anchor: QPointF | None = None
    base_overlay_widget.apply_overlay_window_flags(self, click_through=True)
    self.setGeometry(screen_geometry)
    self._timer = QTimer(self)
    self._timer.setInterval(_ANIMATION_INTERVAL_MS)
    self._timer.timeout.connect(self._on_tick)

  def set_config(self, config: KeyHudConfig) -> None:
    self._config = config
    self.update()

  def update_geometry(self, screen_geometry: QRect) -> None:
    self.setGeometry(screen_geometry)

  def set_cursor_anchor(self, global_pos: QPointF) -> None:
    """僅在 corner == "follow_cursor" 時有意義：記錄游標在本視窗座標系內的位置，供徽章跟隨定位。"""
    top_left = self.geometry().topLeft()
    self._cursor_anchor = QPointF(global_pos.x() - top_left.x(), global_pos.y() - top_left.y())
    if self._badges:
      self.update()

  def on_key_event_pressed(self, key_id: str, display_text: str) -> None:
    now = time.monotonic()
    existing = self._find_badge(key_id)
    if existing is not None and existing.released_at is None:
      # 按住不放時作業系統會持續送出重複按下事件，維持既有徽章即可，不視為新的一次按下
      return
    if existing is not None and now - existing.released_at <= _COMBO_WINDOW_S:
      existing.repeat_count += 1
      existing.created_at = now
      existing.released_at = None
      self._badges.remove(existing)
      self._badges.insert(0, existing)
    else:
      self._badges.insert(0, KeyBadge(key_id=key_id, display_text=display_text, created_at=now))
      if len(self._badges) > self._config.max_visible_badges:
        self._badges = self._badges[: self._config.max_visible_badges]
    self.update()
    self._sync_timer_state()

  def on_key_event_released(self, key_id: str) -> None:
    badge = self._find_badge(key_id)
    if badge is not None and badge.released_at is None:
      badge.released_at = time.monotonic()
      self.update()
      self._sync_timer_state()

  def _find_badge(self, key_id: str) -> KeyBadge | None:
    for badge in self._badges:
      if badge.key_id == key_id:
        return badge
    return None

  def _sync_timer_state(self) -> None:
    """只有存在正在淡出的徽章時才需要持續動畫，按住中的徽章是靜態的，省下閒置時的重繪負擔。"""
    has_fading = any(b.released_at is not None for b in self._badges)
    if has_fading and not self._timer.isActive():
      self._timer.start()
    elif not has_fading and self._timer.isActive():
      self._timer.stop()

  def _on_tick(self) -> None:
    now = time.monotonic()
    fade_s = self._config.fade_duration_ms / 1000.0
    self._badges = [
      b for b in self._badges if b.released_at is None or now - b.released_at <= fade_s
    ]
    self.update()
    self._sync_timer_state()

  def paintEvent(self, event: QPaintEvent) -> None:
    if not self._badges:
      return
    painter = QPainter(self)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = QFont()
    font.setPointSize(self._config.font_size)
    painter.setFont(font)
    metrics = QFontMetrics(font)
    now = time.monotonic()
    fade_s = self._config.fade_duration_ms / 1000.0

    cursor_y, stack_down = self._start_y()

    for badge in self._badges:
      is_held = badge.released_at is None
      opacity = 1.0 if is_held else max(0.0, 1.0 - (now - badge.released_at) / fade_s)
      label = badge.display_text if badge.repeat_count <= 1 else f"{badge.display_text} ×{badge.repeat_count}"
      text_rect = metrics.boundingRect(label)
      box_width = text_rect.width() + _BADGE_PADDING * 2
      box_height = text_rect.height() + _BADGE_PADDING
      x = int(self._start_x(box_width))
      y = int(cursor_y if stack_down else cursor_y - box_height)

      background = QColor(45, 125, 245) if is_held else QColor(0, 0, 0)
      background.setAlphaF((0.75 if is_held else 0.6) * opacity)
      painter.setPen(Qt.PenStyle.NoPen)
      painter.setBrush(background)
      painter.drawRoundedRect(x, y, box_width, box_height, 8, 8)

      if is_held:
        border_color = QColor(255, 255, 255)
        border_color.setAlphaF(0.85)
        painter.setPen(QPen(border_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(x, y, box_width, box_height, 8, 8)

      text_color = QColor(255, 255, 255)
      text_color.setAlphaF(opacity)
      painter.setPen(text_color)
      painter.drawText(x, y, box_width, box_height, Qt.AlignmentFlag.AlignCenter, label)

      if stack_down:
        cursor_y += box_height + _BADGE_SPACING
      else:
        cursor_y -= box_height + _BADGE_SPACING

  def _start_x(self, box_width: int) -> float:
    if self._config.corner == "follow_cursor":
      anchor = self._cursor_anchor or QPointF(self.width() / 2, self.height() / 2)
      return anchor.x() + _FOLLOW_CURSOR_OFFSET
    _, horizontal = self._parse_alignment(self._config.corner)
    if horizontal == "right":
      return self.width() - _MARGIN - box_width
    if horizontal == "center":
      return (self.width() - box_width) / 2
    return _MARGIN

  def _start_y(self) -> tuple[float, bool]:
    """回傳（第一個徽章的起始 y、是否向下堆疊）。"""
    if self._config.corner == "follow_cursor":
      anchor = self._cursor_anchor or QPointF(self.width() / 2, self.height() / 2)
      return anchor.y() + _FOLLOW_CURSOR_OFFSET, True
    vertical, _ = self._parse_alignment(self._config.corner)
    if vertical == "top":
      return _MARGIN, True
    if vertical == "bottom":
      return self.height() - _MARGIN, False
    return self.height() / 2, True

  @staticmethod
  def _parse_alignment(corner: str) -> tuple[str, str]:
    """把 "top-left" 這類設定值拆成 (vertical, horizontal)；"center" 視為 (middle, center)。"""
    if corner == "center":
      return "middle", "center"
    parts = corner.split("-")
    if len(parts) == 2:
      return parts[0], parts[1]
    return "bottom", "left"
