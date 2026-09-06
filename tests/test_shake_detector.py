"""測試搖晃偵測邏輯：注入假時間函式與座標序列，驗證觸發時機。"""
from __future__ import annotations

from app.input.shake_detector import ShakeDetector, ShakeDetectorConfig


class FakeClock:
  def __init__(self) -> None:
    self.now = 0.0

  def __call__(self) -> float:
    return self.now

  def advance(self, seconds: float) -> None:
    self.now += seconds


def _make_detector(clock: FakeClock) -> ShakeDetector:
  config = ShakeDetectorConfig(
    window_ms=700,
    min_reversals=4,
    min_speed_px_per_s=500.0,
    noise_threshold_px=4,
    cooldown_ms=1500,
  )
  return ShakeDetector(config=config, time_fn=clock)


def _shake_burst(detector: ShakeDetector, clock: FakeClock, start_x: int) -> int:
  """模擬一段左右快速反轉的搖晃動作，回傳結束時的 x 座標。"""
  x = start_x
  direction = 1
  for _ in range(10):
    x += direction * 40
    detector.on_mouse_moved(x, 300)
    clock.advance(0.05)
    direction *= -1
  return x


def test_shake_gesture_triggers_signal(qtbot) -> None:
  clock = FakeClock()
  detector = _make_detector(clock)
  triggered = []
  detector.shake_detected.connect(lambda: triggered.append(True))

  _shake_burst(detector, clock, 500)

  assert len(triggered) == 1


def test_normal_movement_does_not_trigger(qtbot) -> None:
  clock = FakeClock()
  detector = _make_detector(clock)
  triggered = []
  detector.shake_detected.connect(lambda: triggered.append(True))

  x = 0
  for _ in range(20):
    x += 20
    detector.on_mouse_moved(x, 300)
    clock.advance(0.05)

  assert triggered == []


def test_cooldown_prevents_immediate_retrigger(qtbot) -> None:
  clock = FakeClock()
  detector = _make_detector(clock)
  triggered = []
  detector.shake_detected.connect(lambda: triggered.append(True))

  x = _shake_burst(detector, clock, 500)
  assert len(triggered) == 1

  clock.advance(0.1)
  x = _shake_burst(detector, clock, x)
  assert len(triggered) == 1  # 冷卻時間內不應再次觸發

  clock.advance(2.0)
  _shake_burst(detector, clock, x)
  assert len(triggered) == 2  # 冷卻結束後應可再次觸發
