"""覆蓋層各效果共用的渲染狀態，所有 OverlayWindow 都讀取同一份狀態繪製。"""
from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QPointF


@dataclass
class ClickRipple:
  global_pos: QPointF
  button: str
  start_time: float


@dataclass
class OverlayRenderState:
  cursor_global_pos: QPointF | None = None
  spotlight_display_pos: QPointF | None = None  # 聚光燈實際繪製位置，平滑追向 cursor_global_pos
  click_ripples: list[ClickRipple] = field(default_factory=list)
  find_cursor_active: bool = False
  find_cursor_start_time: float = 0.0
