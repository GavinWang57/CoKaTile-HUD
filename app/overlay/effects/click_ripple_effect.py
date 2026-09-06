"""點擊漣漪動畫：純狀態計算（可 unit test）與 Qt 繪製。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter

from app.config import ClickEffectConfig
from app.overlay.render_state import ClickRipple


@dataclass
class RippleVisual:
  radius: float
  opacity: float


def compute_ripple_state(
  ripple: ClickRipple, now: float, duration_ms: int, max_radius: float
) -> RippleVisual | None:
  """依經過時間內插漣漪半徑（0→max_radius）與透明度（1→0），超過 duration 回傳 None 代表應剔除。"""
  elapsed_ms = (now - ripple.start_time) * 1000.0
  if elapsed_ms < 0 or elapsed_ms > duration_ms:
    return None
  progress = elapsed_ms / duration_ms
  return RippleVisual(radius=max_radius * progress, opacity=1.0 - progress)


def paint(
  painter: QPainter,
  ripples: Iterable[ClickRipple],
  to_local: Callable[[QPointF], QPointF],
  now: float,
  config: ClickEffectConfig,
) -> None:
  for ripple in ripples:
    visual = compute_ripple_state(ripple, now, config.duration_ms, config.max_radius)
    if visual is None:
      continue
    color = QColor(config.left_color if ripple.button == "left" else config.right_color)
    color.setAlphaF(max(0.0, visual.opacity))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    local_pos = to_local(ripple.global_pos)
    painter.drawEllipse(local_pos, visual.radius, visual.radius)
