"""測試點擊漣漪動畫的半徑/透明度內插邏輯。"""
from __future__ import annotations

import pytest
from PySide6.QtCore import QPointF

from app.overlay.effects.click_ripple_effect import compute_ripple_state
from app.overlay.render_state import ClickRipple


def test_ripple_interpolates_over_time() -> None:
  ripple = ClickRipple(global_pos=QPointF(0, 0), button="left", start_time=10.0)

  start = compute_ripple_state(ripple, now=10.0, duration_ms=400, max_radius=60)
  midpoint = compute_ripple_state(ripple, now=10.2, duration_ms=400, max_radius=60)

  assert start is not None
  assert start.radius == 0
  assert start.opacity == 1.0
  assert midpoint is not None
  assert midpoint.radius == pytest.approx(30)
  assert midpoint.opacity == pytest.approx(0.5)


def test_ripple_expires_after_duration() -> None:
  ripple = ClickRipple(global_pos=QPointF(0, 0), button="left", start_time=10.0)
  assert compute_ripple_state(ripple, now=10.5, duration_ms=400, max_radius=60) is None
