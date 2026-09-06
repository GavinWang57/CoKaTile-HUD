"""測試聚光燈平滑跟隨演算法：應逐步收斂，且與目標的距離不超過 max_lag。"""
from __future__ import annotations

import pytest
from PySide6.QtCore import QPointF

from app.overlay.overlay_manager import _compute_smoothed_position


def test_converges_when_close_enough() -> None:
  current = QPointF(100, 100)
  target = QPointF(100.2, 100.1)

  new_pos, animating = _compute_smoothed_position(current, target, smoothing=0.3, max_lag=45)

  assert animating is False
  assert new_pos == target


def test_moves_toward_target_without_exceeding_max_lag() -> None:
  current = QPointF(0, 0)
  target = QPointF(1000, 0)

  new_pos, animating = _compute_smoothed_position(current, target, smoothing=0.3, max_lag=45)

  assert animating is True
  assert (target.x() - new_pos.x()) == pytest.approx(45, abs=1e-6)
  assert new_pos.x() > current.x()


def test_small_step_not_clamped() -> None:
  current = QPointF(0, 0)
  target = QPointF(10, 0)

  new_pos, animating = _compute_smoothed_position(current, target, smoothing=0.3, max_lag=45)

  assert animating is True
  assert new_pos.x() == pytest.approx(3.0)


def test_repeated_steps_eventually_converge() -> None:
  current = QPointF(0, 0)
  target = QPointF(200, 0)
  animating = True
  steps = 0

  while animating and steps < 1000:
    current, animating = _compute_smoothed_position(current, target, smoothing=0.3, max_lag=45)
    assert abs(target.x() - current.x()) <= 45 + 1e-6
    steps += 1

  assert animating is False
  assert current == target
