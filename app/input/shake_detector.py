"""偵測滑鼠快速搖晃（方向反覆反轉）手勢，用來觸發「尋找游標」輔助。"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QObject, Signal


@dataclass
class ShakeDetectorConfig:
  window_ms: int = 700
  min_reversals: int = 4
  min_speed_px_per_s: float = 800.0
  noise_threshold_px: int = 4
  cooldown_ms: int = 1500


class ShakeDetector(QObject):
  shake_detected = Signal()

  def __init__(
    self,
    config: ShakeDetectorConfig | None = None,
    time_fn: Callable[[], float] = time.monotonic,
    parent: QObject | None = None,
  ):
    super().__init__(parent)
    self._config = config or ShakeDetectorConfig()
    self._time_fn = time_fn
    self._samples: deque[tuple[float, int, int]] = deque(maxlen=32)
    self._reversals: deque[float] = deque()
    self._last_direction = 0
    self._last_shake_at = float("-inf")

  def set_config(self, config: ShakeDetectorConfig) -> None:
    self._config = config

  def reset(self) -> None:
    self._samples.clear()
    self._reversals.clear()
    self._last_direction = 0

  def on_mouse_moved(self, x: int, y: int) -> None:
    now = self._time_fn()
    if self._samples:
      _, last_x, _ = self._samples[-1]
      dx = x - last_x
      if abs(dx) >= self._config.noise_threshold_px:
        direction = 1 if dx > 0 else -1
        if self._last_direction != 0 and direction != self._last_direction:
          self._reversals.append(now)
        self._last_direction = direction
    self._samples.append((now, x, y))
    self._trim_old(now)
    self._maybe_trigger(now)

  def _trim_old(self, now: float) -> None:
    window_s = self._config.window_ms / 1000.0
    while self._reversals and now - self._reversals[0] > window_s:
      self._reversals.popleft()
    while len(self._samples) > 1 and now - self._samples[0][0] > window_s:
      self._samples.popleft()

  def _current_speed(self) -> float:
    """用視窗內取樣點的總路徑長度除以時間，而非首尾位移，避免來回搖晃時位移互相抵消。"""
    if len(self._samples) < 2:
      return 0.0
    samples = list(self._samples)
    total_distance = 0.0
    for (_, x0, y0), (_, x1, y1) in zip(samples, samples[1:]):
      total_distance += ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    elapsed = samples[-1][0] - samples[0][0]
    if elapsed <= 0:
      return 0.0
    return total_distance / elapsed

  def _maybe_trigger(self, now: float) -> None:
    cooldown_s = self._config.cooldown_ms / 1000.0
    if now - self._last_shake_at < cooldown_s:
      return
    if len(self._reversals) < self._config.min_reversals:
      return
    if self._current_speed() < self._config.min_speed_px_per_s:
      return
    self._last_shake_at = now
    self._reversals.clear()
    self.shake_detected.emit()
