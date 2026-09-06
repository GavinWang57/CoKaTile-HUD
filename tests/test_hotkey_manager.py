"""測試熱鍵組合偵測：需完全按下設定組合才觸發，且需放開後才能再次觸發。"""
from __future__ import annotations

from app.input.hotkey_manager import HotkeyManager, parse_hotkey


def test_parse_hotkey_normalizes_names() -> None:
  assert parse_hotkey("<ctrl>+<alt>+l") == frozenset({"ctrl", "alt", "l"})


def test_triggers_only_when_full_combo_pressed(qtbot) -> None:
  manager = HotkeyManager("<ctrl>+<alt>+l")
  triggered = []
  manager.hotkey_triggered.connect(lambda: triggered.append(True))

  manager.on_key_pressed("ctrl")
  manager.on_key_pressed("alt")
  assert triggered == []

  manager.on_key_pressed("l")
  assert len(triggered) == 1


def test_requires_full_release_before_retrigger(qtbot) -> None:
  manager = HotkeyManager("<ctrl>+<alt>+l")
  triggered = []
  manager.hotkey_triggered.connect(lambda: triggered.append(True))

  for key in ("ctrl", "alt", "l"):
    manager.on_key_pressed(key)
  assert len(triggered) == 1

  manager.on_key_pressed("l")  # 持續按住不應重複觸發
  assert len(triggered) == 1

  manager.on_key_released("l")
  manager.on_key_released("alt")
  manager.on_key_released("ctrl")

  for key in ("ctrl", "alt", "l"):
    manager.on_key_pressed(key)
  assert len(triggered) == 2
